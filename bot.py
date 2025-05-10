import discord
from discord.ext import commands
import os
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
    try:
        synced = await client.tree.sync()
        if (len(synced) == 1): plural = ""
        else: plural = 's'
        print(f"Synced {len(synced)} command{plural}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    for cog in os.listdir('cogs'):
        if cog.endswith('.py'):
            try:
                await client.load_extension(f'cogs.{cog[:-3]}')
                print (f"Loaded {cog}")
            except Exception as e:
                print(f'Failed to load extension {cog}: {e}')

@client.tree.command(name="reload", description="Reloads bot cogs. Can only be used by the bot's owner.")
async def reload(interaction: discord.Interaction):
    if(interaction.user.id == variables["owner_id"]):
        str = ""
        try:
            for cog in os.listdir('cogs'):
                if cog.endswith('.py'):
                    try:
                        await client.load_extension(f'cogs.{cog[:-3]}')
                        str += f"\nLoaded {cog}"
                    except commands.ExtensionAlreadyLoaded:
                        await client.reload_extension(f'cogs.{cog[:-3]}')
                        str+= f"\nReloaded {cog}"
                    except Exception as e:
                        str += f'Failed to load extension {cog}: {e}\n'
            await interaction.response.send_message(f"Cogs reloaded:{str}", ephemeral=True)
        except:
            await interaction.response.send_message(f"Cogs failed to reload:{str}", ephemeral=True)
    else:
        await interaction.response.send_message("Only the bot's owner can use this command.", ephemeral=True)

@client.tree.command(name="tags", description="Sends the Danbooru tag group wiki link and optionally tags a user.")
async def tags(interaction: discord.Interaction, user: discord.Member = None):
    button = discord.ui.Button(label='Danbooru Tag Group Wiki', url='https://danbooru.donmai.us/wiki_pages/tag_groups')
    view = discord.ui.View().add_item(button)

    if user:
        await interaction.response.send_message(f"{user.mention} Here is the Danbooru tag group wiki.", view=view)
    else:
        await interaction.response.send_message('Here is the Danbooru tag group wiki.', view=view)

@client.tree.command(name="help", description="See more info about commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="Command List", description="Here are the available commands:", color=0x00ff00)
    embed.add_field(name="/help", value="Displays this help message.", inline=False)
    embed.add_field(name="/tags", value="Sends the Danbooru tag group wiki link and optionally tags a user.", inline=False)
    embed.add_field(name="AI Features", value="To use the AI features, simply mention the bot in a message, or reply to a message the bot sent. The bot will reply to your message, taking the whole reply chain as context.", inline=False)
    embed.add_field(name="AI-based join and leave messages", value="Activate automatically when a member joins or leaves.", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

client.run(keys["client_key"])
