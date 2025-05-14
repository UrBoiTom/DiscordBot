from discord.ext import commands
import json

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

def has_name(backup_name, message):
    if(message.guild): return message.guild.me.display_name.lower() in message.content.lower()
    else: return backup_name.lower() in message.content.lower()