import json
import discord
import importlib
from PIL import Image
import requests
from io import BytesIO

def reload(module):
    importlib.reload(module)

def load_json(filename):
    filepath = f'variables/{filename}.json'
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

def has_name(backup_name, message):
    if(message.guild): return message.guild.me.display_name.lower() in message.content.lower()
    else: return backup_name.lower() in message.content.lower()

def sort_content(message):
    if message.attachments:
        output = []
        has_images = False
        for attachment in message.attachments:
            if "image" in attachment.content_type:
                has_images = True
                output.append(Image.open(BytesIO(requests.get(attachment.url).content)))
        if(has_images):
            output.append(f"Sender ID: {message.author.id}\nSender Name: {message.author.display_name}\nMessage: {message.content}")
            return output
    return f"Sender ID: {message.author.id}\nSender Name: {message.author.display_name}\nMessage: {message.content}"