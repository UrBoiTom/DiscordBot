import json
import discord
import importlib
from PIL import Image
import requests
from io import BytesIO
import re

def reload(module):
    importlib.reload(module)

def load_json(filename):
    filepath = f'Variables/{filename}.json'
    try:
        with open(filepath) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{filepath}' not found.")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from '{filepath}'. Check the file format. Details: {e}")
        raise # Re-raise the exception

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

variables = load_json("general")

def has_name(backup_name, message, bot):
    nicknames = variables[bot]["nicknames"]
    if(message.guild): nicknames.append(message.guild.me.display_name)
    else: nicknames.append(backup_name)
    for nickname in nicknames:
        if re.search(fr"\b({nickname.lower()})\b", message.content.lower()):
            return True
    return False

def image_context(message, prompt):
    if message.attachments:
        output = []
        has_images = False
        for attachment in message.attachments:
            if "image" in attachment.content_type:
                has_images = True
                output.append(image(attachment.url))
        if(has_images):
            output.append(prompt)
            return output
    return prompt

def image(url):
    return Image.open(BytesIO(requests.get(url).content))
