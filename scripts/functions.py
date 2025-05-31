import json
import discord
import importlib
from PIL import Image
import requests
from io import BytesIO
import asyncio
import re
import os
from google import genai
from google.genai import types # type: ignore

def reload(module):
    importlib.reload(module)

def load_json(filepath):
    filepath = f'{os.path.join(*filepath.split("/"))}.json'
    try:
        with open(filepath) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{filepath}' not found.")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from '{filepath}'. Check the file format. Details: {e}")
        raise # Re-raise the exception

def save_json(data, filepath):
    filepath = f'{os.path.join(*filepath.split("/"))}.json'
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error: Could not save JSON to '{filepath}'. Details: {e}")
        raise # Re-raise the exception


async def get_message_history_context(current_message: discord.Message, limit: int):
    """
    Fetches the last 'limit' messages from the channel (before current_message)
    and formats them for AI context.
    Returns a list of context parts (PIL.Image.Image objects or strings),
    ordered from oldest to newest. For each message, images come before text.
    """
    context_parts = []
    if limit <= 0:
        return context_parts
        
    messages_history = []
    # Fetch messages before the current one. discord.py's history is newest first.
    async for msg in current_message.channel.history(limit=limit, before=current_message):
        messages_history.append(msg)

    # Reverse to process from oldest to newest
    for msg in reversed(messages_history):
        msg_specific_parts = []
        # Handle images for this historical message
        if msg.attachments:
            for attachment in msg.attachments:
                if attachment.content_type and "image" in attachment.content_type:
                    try:
                        img_obj = image(attachment.url) # image() returns PIL.Image
                        msg_specific_parts.append(img_obj)
                    except Exception as e:
                        print(f"Error processing image from historical message {msg.id} ({attachment.filename}): {e}")
        
        timestamp_str = msg.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')
        text_part = f"Timestamp: {timestamp_str}\nSender ID: {msg.author.id}\nSender Name: {msg.author.display_name}\nMessage: {msg.content}\n"
        msg_specific_parts.append(text_part)
        context_parts.extend(msg_specific_parts)
    return context_parts

variables = load_json("Variables/general")

def has_name(backup_name, message, bot):
    nicknames = variables[bot]["nicknames"]
    if(message.guild): nicknames.append(message.guild.me.display_name)
    else: nicknames.append(backup_name)
    for nickname in nicknames:
        if re.search(fr"\b({nickname.lower()})\b", message.content.lower()):
            return True
    return False

async def chunkify(message:str):
    if len(message) > 2000:
        sentences = re.split("([.!?]+)", message)
        current_chunk = ""
        chunks = []
        for sentence in sentences:
            if len(current_chunk + sentence) > 2000:
                chunks.append(current_chunk)
                current_chunk = sentence
            else:
                current_chunk += sentence
        return chunks
    else:
        return [message]
    
async def send_message(message, chunks):
    await message.reply(chunks[0])
    for chunk in chunks[1:]:
        await message.channel.send(chunk)

keys = load_json('Variables/keys')
genai_client = genai.Client(api_key=keys["ai_studio_key"])

async def generate_audio(message, config):
    voice_prompt = config["voice_prompt"]
    def _blocking_generate_audio():
        return genai_client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=f"{voice_prompt}: {message}",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voices(config["voice_gender"]),
                    )
                )
            ),
        )
    )
    response = await asyncio.wait_for(asyncio.to_thread(_blocking_generate_audio), timeout=180)
    return response.candidates[0].content.parts[0].inline_data.data

def get_voice_prompt(id):
    if f"{str(id)}.json" in os.listdir(os.path.join("config", "voice")):
        path = f"config/voice/{str(id)}"
    else:
        path = "config/default_voice"
    return load_json(path)

def voices(num):
    switcher = {
        0: "Algenib",
        1: "Aoede",
    }
    return switcher.get(num, "Zephyr")

def image(url):
    return Image.open(BytesIO(requests.get(url).content))
