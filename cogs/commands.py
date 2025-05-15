import discord
from discord import app_commands
from discord.ext import commands
import os
import subprocess
import scripts.functions as functions
functions.reload(functions)

variables = functions.load_json('general')

class Commands(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="reload", description="Reloads bot cogs. Can only be used by the bot's owner.")
    @app_commands.choices(part=[
            app_commands.Choice(name="Cogs", value="cogs"),
            app_commands.Choice(name="Commands", value="commands"),
            ])
    async def reload(self, interaction: discord.Interaction, part: app_commands.Choice[str]):
        if(interaction.user.id == variables["owner_id"]):
            if(part.value == "cogs"):
                string = ""
                try:
                    for cog in os.listdir('cogs'):
                        if cog.endswith('.py'):
                            try:
                                await self.client.load_extension(f'cogs.{cog[:-3]}')
                                string += f"\nLoaded {cog}"
                            except commands.ExtensionAlreadyLoaded:
                                await self.client.reload_extension(f'cogs.{cog[:-3]}')
                                string+= f"\nReloaded {cog}"
                            except Exception as e:
                                string += f'\nFailed to load extension {cog}: {e}\n'
                    
                    await interaction.response.send_message(f"Cogs reloaded:{string}", ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message(f"Cogs failed to reload:{e}", ephemeral=True)
            elif (part.value == "commands"):
                try:
                    synced = await self.client.tree.sync()
                    if (len(synced) == 1): plural = ""
                    else: plural = 's'
                    await interaction.response.send_message(f"Synced {len(synced)} command{plural}", ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message(f"Failed to sync commands: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"Part not recognised", ephemeral=True)

        else:
            await interaction.response.send_message("Only the bot's owner can use this command.", ephemeral=True)

    @app_commands.command(name="update", description="Pulls the latest code from the repository. Can only be used by the bot's owner.")
    async def update(self, interaction: discord.Interaction):
        if interaction.user.id == variables["owner_id"]:
            await interaction.response.defer(ephemeral=True)
            try:
                # Run the git pull command
                git_pull_result = subprocess.run(
                    ['git', 'pull', '--rebase', '--autostash'],
                    capture_output=True,
                    text=True, # Capture output as text
                    cwd='.', # Run in the current directory (bot's root)
                    check=True # Raise CalledProcessError if command returns non-zero exit code
                )
                git_output = git_pull_result.stdout.strip()
                if git_pull_result.stderr:
                    git_output += f"\n\nGit Stderr:\n{git_pull_result.stderr.strip()}"

                pip_output = "Pip install not attempted."
                try:
                    # Run pip install command
                    pip_install_result = subprocess.run(
                        ['pip', 'install', '-U', '-r', 'requirements.txt'],
                        capture_output=True,
                        text=True,
                        cwd='.',
                        check=True
                    )
                    pip_output = pip_install_result.stdout.strip()
                    if pip_install_result.stderr:
                        pip_output += f"\n\nPip Stderr:\n{pip_install_result.stderr.strip()}"
                    await interaction.followup.send(f"Update successful:\n\nGit Pull:\n```\n{git_output}\n```\nPip Install Successful", ephemeral=True)
                except subprocess.CalledProcessError as e_pip:
                    pip_fail_output = f"Pip install failed:\n```\n{e_pip.stdout.strip()}\n{e_pip.stderr.strip()}\n```"
                    await interaction.followup.send(f"Git pull successful, but Pip install failed:\n\nGit Pull:\n```\n{git_output}\n```\n\n{pip_fail_output}", ephemeral=True)
                except Exception as e_pip_general:
                    await interaction.followup.send(f"Git pull successful, but an error occurred during pip install: {e_pip_general}", ephemeral=True)
            except subprocess.CalledProcessError as e:
                await interaction.followup.send(f"Git pull failed:\n```\n{e.stdout.strip()}\n{e.stderr.strip()}\n```", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"An error occurred during git pull: {e}", ephemeral=True)
        else:
            await interaction.response.send_message("Only the bot's owner can use this command.", ephemeral=True)

    @app_commands.command(name="tags", description="Sends the Danbooru tag group wiki link and optionally tags a user.")
    async def tags(self, interaction: discord.Interaction, user: discord.Member = None):
        button = discord.ui.Button(label='Danbooru Tag Group Wiki', url='https://danbooru.donmai.us/wiki_pages/tag_groups')
        view = discord.ui.View().add_item(button)

        if user:
            await interaction.response.send_message(f"{user.mention} Here is the Danbooru tag group wiki.", view=view)
        else:
            await interaction.response.send_message('Here is the Danbooru tag group wiki.', view=view)

    
    @app_commands.command(name="help", description="See more info about commands")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Command List", description="Here are the available commands:", color=0x00ff00)
        embed.add_field(name="/help", value="Displays this help message.", inline=False)
        embed.add_field(name="/tags", value="Sends the Danbooru tag group wiki link and optionally tags a user.", inline=False)
        embed.add_field(name="/update", value="Pulls the latest code from the repository (Owner only).", inline=False)
        embed.add_field(name="AI Features", value="To use the AI features, simply mention the bot in a message, or reply to a message the bot sent. The bot will reply to your message, taking the whole reply chain as context.", inline=False)
        embed.add_field(name="AI-based join and leave messages", value="Activate automatically when a member joins or leaves.", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(client):
    await client.add_cog(Commands(client))