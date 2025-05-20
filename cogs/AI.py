import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from google.genai import types # type: ignore
import re
from datetime import timedelta
import asyncio
import scripts.functions as functions
functions.reload(functions)


keys = functions.load_json('keys')
prompts = functions.load_json('prompts')
variables = functions.load_json('general')
modules = functions.load_json('modules')

genai_client = genai.Client(api_key=keys["ai_studio_key"])

class AI(commands.Cog):
    def __init__(self, client):
        self.client = client

    
    @app_commands.command(name="message", description="Activates the AI features through a command.")
    async def message(self, interaction: discord.Interaction, msg: str, img: discord.Attachment = None):
        await interaction.response.defer(thinking=True)
        prompt = f"Sender ID: {interaction.user.id}\nSender Name: {interaction.user.display_name}\nMessage: {msg}"
        if img and "image" in img.content_type:
            prompt = [functions.image(img.url), prompt]
        print(f"\n----------------------- AI PROMPT -----------------------\n{prompt}")
        if(variables["ai_provider"] == "ai_studio"):
            output = await aistudio_request(prompt, prompts[self.client.main_name]["system_prompt"])
        chunks = await functions.chunkify(output)
        await interaction.edit_original_response(content=chunks[0])
        for chunk in chunks[1:]:
            await interaction.channel.send(chunk)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.client.user:
            if(modules[self.client.main_name]["Timeout"]):
                if(re.search(r"!Timeout <@[0-9]+>", message.content)):
                    for string in re.findall(r"!Timeout <@[0-9]+>", message.content):
                        member = message.guild.get_member(int(re.search(r"[0-9]+", string).group(0)))
                        await member.timeout(timedelta(minutes=variables["timeout_duration_minutes"]), reason=variables["timeout_reason"])
            return
        if message.author.bot:
            return

        if(modules[self.client.main_name]["Main"]):
            if self.client.user in message.mentions or functions.has_name(self.client.user.display_name, message, self.client.main_name):
                async with message.channel.typing():
                    final_prompt_parts = []

                    # 1. Get historical context
                    history_limit = variables["ai_message_history_limit"] # Default to 5 messages

                    if history_limit > 0:
                        historical_context_parts = await functions.get_message_history_context(message, history_limit)
                        final_prompt_parts.extend(historical_context_parts)

                    # 2. Add current message's context (images first, then text)
                    current_message_images = []
                    if message.attachments:
                        for attachment in message.attachments:
                            if "image" in attachment.content_type:
                                try:
                                    current_message_images.append(functions.image(attachment.url))
                                except Exception as e:
                                    print(f"Error processing image from current message {message.id} ({attachment.filename}): {e}")
                    final_prompt_parts.extend(current_message_images)

                    timestamp_str = message.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')
                    current_message_text = f"Timestamp: {timestamp_str}\nSender ID: {message.author.id}\nSender Name: {message.author.display_name}\nMessage: {message.content}\n"

                    final_prompt_parts.append(current_message_text)

                    # 3. Determine final prompt format for genai
                    has_images = any(not isinstance(p, str) for p in final_prompt_parts)
                    prompt_to_send = final_prompt_parts if has_images else "".join(final_prompt_parts)

                    print(f"\n----------------------- AI PROMPT -----------------------\n{prompt_to_send}")
                    if(variables["ai_provider"] == "ai_studio"):
                        output = await aistudio_request(prompt_to_send, prompts[self.client.main_name]["system_prompt"])
                    chunks = await functions.chunkify(output)
                    await functions.send_message(message, chunks)
        if(modules[self.client.main_name]["Welcome"]):
            if message.type == discord.MessageType.new_member:
                async with message.channel.typing():
                    prompt = f"New User ID: {message.author.id}\nNew User Name: {message.author.display_name}"
                    print(f"\n--------------------- NEW MEMBER ---------------------\n{prompt}")
                    if(variables["ai_provider"] == "ai_studio"):
                        output = await aistudio_request(prompt, prompts[self.client.main_name]["system_prompt"] + prompts["welcome_system_prompt"], variables["welcome_goodbye_model_index"])
                    chunks = await functions.chunkify(output)
                    await functions.send_message(message, chunks)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if(modules[self.client.main_name]["Goodbye"]):
            if member.guild.system_channel:
                prompt = f"\nServer Name: {member.guild.name}\nUser that left ID: {member.id}\nUser that left name: {member.display_name}"
                print(f"\n--------------------- MEMBER LEAVE ---------------------\n{prompt}")
                if(variables["ai_provider"] == "ai_studio"):
                    output = await aistudio_request(prompt, prompts[self.client.main_name]["system_prompt"] + prompts["goodbye_system_prompt"], variables["welcome_goodbye_model_index"])
                await member.guild.system_channel.send(output)

async def aistudio_request(prompt, system_prompt, modelIndex = variables["default_ai_model_index"]):
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(genai_client.models.generate_content,
                model=variables["models"]["ai_studio"][modelIndex],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=[
                        types.Tool(
                            google_search = types.GoogleSearch()
                        )
                    ],
                ),
                contents = prompt
            ),
            timeout=180
            )
        output = response.text
    except IndexError:
        print(f"\n------------------------- AI ERROR -------------------------\nError: No more models available to try after index {modelIndex}.")
        output = "Sorry, I encountered an issue processing your request with all available AI models."
    except Exception as e:
        print(f"\n------------------------- AI ERROR -------------------------\nError with model index {modelIndex}: {e}")
        try:
            print(f"Trying next model index: {modelIndex + 1}")
            output = await aistudio_request(prompt, system_prompt, modelIndex + 1)
        except IndexError:
            print(f"\n------------------------- AI ERROR -------------------------\nError: No more models available to try after index {modelIndex}.")
            output = "Sorry, I encountered an issue processing your request with all available AI models."
        except Exception as final_e:
            print(f"\n------------------------- AI ERROR -------------------------\nError during retry: {final_e}")
            output = "Sorry, I encountered an unexpected error while processing your request."

    output = re.sub(r"(.|\n)*Message: ", "", output)
    return output

async def setup(client):
    await client.add_cog(AI(client))
