import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from google.genai import types # type: ignore
import re
from datetime import timedelta
import asyncio
from scripts.functions import load_json

keys = load_json('keys')
prompts = load_json('prompts')
variables = load_json('general')
modules = load_json('modules')

genai_client = genai.Client(api_key=keys["ai_studio_key"])

class AI(commands.Cog):
    def __init__(self, client):
        self.client = client

    
    @app_commands.command(name="message", description="Activates the AI features through a command.")
    async def message(self, interaction: discord.Interaction, msg: str):
        await interaction.response.defer(thinking=True)
        prompt = f"Sender ID: {interaction.user.id}\nSender Name: {interaction.user.display_name}\nMessage: {msg}"
        print(f"\n----------------------- AI PROMPT -----------------------\n{prompt}")
        if(variables["ai_provider"] == "ai_studio"):
            output = await aistudio_request(prompt, prompts["system_prompt"])
        print("ready")
        await interaction.edit_original_response(content=output)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.client.user:
            if(modules["Timeout"]):
                if(re.search(r"!Timeout <@[0-9]+>", message.content)):
                    for str in re.findall(r"!Timeout <@[0-9]+>", message.content):
                        member = message.guild.get_member(int(re.search(r"[0-9]+", str).group(0)))
                        await member.timeout(timedelta(minutes=5), reason="Because Riley said so.")
            return

        if(modules["Main"]):
            if self.client.user in message.mentions or self.client.user.display_name in message.content:
                async with message.channel.typing():
                    prompt = f"Sender ID: {message.author.id}\nSender Name: {message.author.display_name}\nMessage: {message.content}"
                    prompt = await get_replies(message, prompt)
                    print(f"\n----------------------- AI PROMPT -----------------------\n{prompt}")
                    if(variables["ai_provider"] == "ai_studio"):
                        output = await aistudio_request(prompt, prompts["system_prompt"])
                    await message.reply(output)

        if(modules["Welcome"]):
            if message.type == discord.MessageType.new_member:
                async with message.channel.typing():
                    prompt = f"New User ID: {message.author.id}\nNew User Name: {message.author.display_name}"
                    print(f"\n--------------------- NEW MEMBER ---------------------\n{prompt}")
                    if(variables["ai_provider"] == "ai_studio"):
                        output = await aistudio_request(prompt, prompts["system_prompt"] + prompts["welcome_system_prompt"], variables["welcome_goodbye_model_index"])
                    await message.reply(output)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if(modules["Goodbye"]):
            if member.guild.system_channel:
                prompt = f"\nServer Name: {member.guild.name}\nUser that left ID: {member.id}\nUser that left name: {member.display_name}"
                print(f"\n--------------------- MEMBER LEAVE ---------------------\n{prompt}")
                if(variables["ai_provider"] == "ai_studio"):
                    output = await aistudio_request(prompt, prompts["system_prompt"] + prompts["goodbye_system_prompt"], variables["welcome_goodbye_model_index"])
                await member.guild.system_channel.send(output)

async def aistudio_request(prompt, system_prompt, modelIndex = 0):
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(genai_client.models.generate_content,
                model=variables["models"]["ai_studio"][modelIndex],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt
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

async def get_replies(message, string):
    cachingLog = ""
    while(message.reference and not isinstance(message.reference.resolved, discord.DeletedReferencedMessage)):
        if(message.reference.cached_message):
            message = message.reference.cached_message
            cachingLog += "C"
        else:
            if(message.reference.resolved):
                message = message.reference.resolved
                cachingLog += "R"
            else:
                try:
                    message = await message.channel.fetch_message(message.reference.message_id)
                    cachingLog += "X"
                except discord.NotFound:
                    print(f"Warning: Could not fetch referenced message {message.reference.message_id}. Stopping reply chain traversal.")
                    break
                except discord.HTTPException as e:
                    print(f"Warning: Discord API error fetching message {message.reference.message_id}: {e}. Stopping reply chain traversal.")
                    break

        string = f"Sender ID: {message.author.id}\nSender Name: {message.author.display_name}\nMessage: {message.content}\n{string}"

    if(cachingLog != ""):
        print(f"\n-------------------- REPLY CACHING LOG --------------------\n{cachingLog}")
    return string

async def setup(client):
    await client.add_cog(AI(client))
