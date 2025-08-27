import discord
from discord.ext import commands
import os
import sys
import scripts.functions as functions

def main():
    name = sys.argv[1]

    keys = functions.load_json('Variables/keys')

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    contexts = discord.app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True)

    client = commands.Bot(command_prefix='/', intents=intents, allowed_contexts=contexts)
    client.main_name = name

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

    client.run(keys[name]["client_key"])

if __name__ == '__main__':
    main()
