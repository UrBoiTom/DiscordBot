# This example requires the 'message_content' intent.

import discord
import json
from google import genai
from google.genai import types # type: ignore
import re

with open('keys.json') as f:
    keys = json.load(f)
    f.close()
with open('prompts.json') as f:
    prompts = json.load(f)
    f.close()
with open('variables.json') as f:
    variables = json.load(f)
    f.close()

genai_client = genai.Client(api_key=keys["ai_studio_key"])

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
client.tree = discord.app_commands.CommandTree(client)

ai_provider = "ai_studio"

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    try:
        synced = await client.tree.sync()
        if (len(synced) == 1): plural = ""
        else: plural = 's'
        print(f"Synced {len(synced)} command{plural}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@client.tree.command(name="tags", description="Sends the Danbooru tag group wiki link and optionally tags a user.")
async def tags(interaction: discord.Interaction, user: discord.Member = None):
    if user:
        await interaction.response.send_message(f"{user.mention} Here is the Danbooru tag group wiki.", view=discord.ui.View().add_item(discord.ui.Button(label='Danbooru Tag Group Wiki', url='https://danbooru.donmai.us/wiki_pages/tag_group')))
    else:
        await interaction.response.send_message('Here is the Danbooru tag group wiki.', view=discord.ui.View().add_item(discord.ui.Button(label='Danbooru Tag Group Wiki', url='https://danbooru.donmai.us/wiki_pages/tag_group')))

@client.tree.command(name="help", description="See more info about commands")
async def tags(interaction: discord.Interaction):
    embed = discord.Embed(title="Command List", description="Here are the available commands:", color=0x00ff00)
    embed.add_field(name="/help", value="Displays this help message.", inline=False)
    embed.add_field(name="/tags", value="Sends the Danbooru tag group wiki link and optionally tags a user.", inline=False)
    embed.add_field(name="AI Features", value="To use the AI features, simply mention the bot in a message, or reply to a message the bot sent. The bot will reply to your message, taking the whole reply chain as context.", inline=False)
    await interaction.response.send_message(embed=embed)




@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if client.user in message.mentions or client.user.display_name in message.content:
        async with message.channel.typing(): 
            prompt = f"Sender ID: {message.author.id}\nSender Name: {message.author.display_name}\nMessage: {message.content}"
            prompt = await get_replies(message, prompt)
            print(prompt)
            if(ai_provider == "ai_studio"):
                output = await aistudio_request(prompt, prompts["system_prompt"])
        await message.reply(output)

    if message.type == discord.MessageType.new_member:
        async with message.channel.typing(): 
            prompt = f"New User ID: {message.author.id}\nNew User Name: {message.author.display_name}"
            print(f"\n---------------------------------------------------------------------------\n{prompt}")
            if(ai_provider == "ai_studio"):
                output = await aistudio_request(prompt, prompts["system_prompt"] + prompts["welcome_system_prompt"], 1)
        await message.reply(output)

async def aistudio_request(prompt, system_prompt, modelIndex = 0):
    try:
        response = genai_client.models.generate_content(
            model=variables["models"]["ai_studio"][modelIndex],
            config=types.GenerateContentConfig(
                system_instruction=system_prompt
            ),
            contents = prompt
        )
        output = response.text
    except Exception as e:
        print(f"\n---------------------------------------------------------------------------\nError: {e}")
        output = await aistudio_request(prompt, modelIndex+1)
    output = re.sub("Sender ID: [0-9]+\nSender Name: [A-Za-z0-9#]+\nMessage: ", "", output)
    return output


async def get_replies(message, string):
    cachingLog = ""
    while(message.reference and not isinstance(message.reference.resolved, discord.DeletedReferencedMessage)):
        if(message.reference.cached_message):
            message = message = message.reference.cached_message
            cachingLog = cachingLog + "1"
        else:
            if(message.reference.resolved):
                message = message.reference.resolved
                cachingLog = cachingLog + "2"
            else:
                message = await message.channel.fetch_message(message.reference.message_id)
                cachingLog = cachingLog + "3"
        string = f"Sender ID: {message.author.id}\nSender Name: {message.author.display_name}\nMessage: {message.content}\n{string}"
    print(f"\n---------------------------------------------------------------------------\n{cachingLog}\n")
    return string

client.run(keys["client_key"])