import discord
from discord.ext import commands
import os
from discord import app_commands
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

keys = load_json('keys')
variables = load_json('general')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = commands.Bot(command_prefix='/', intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

    for cog in os.listdir('cogs'):
        if cog.endswith('.py'):
            try:
                await client.load_extension(f'cogs.{cog[:-3]}')
                print (f"Loaded {cog}")
            except Exception as e:
                print(f'Failed to load extension {cog}: {e}')
    
    try:
        synced = await client.tree.sync()
        if (len(synced) == 1): plural = ""
        else: plural = 's'
        print(f"Synced {len(synced)} command{plural}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

client.run(keys["client_key"])
