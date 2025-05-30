import discord
from discord import app_commands
from discord.ext import commands
import os
import subprocess
import scripts.functions as functions
functions.reload(functions)

variables = functions.load_json('Variables/general')
default_config = functions.load_json('config/default_config')
modules = []
for module in default_config["Modules"]:
    modules.append(app_commands.Choice(name=module, value=module))

class Commands(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def is_owner(interaction: discord.Interaction):
        return interaction.user.id == variables["owner_id"]

    @app_commands.command(name="reload", description="Reloads bot cogs. Can only be used by the bot's owner.")
    @app_commands.check(is_owner)
    @app_commands.choices(part=[
            app_commands.Choice(name="Cogs", value="cogs"),
            app_commands.Choice(name="Commands", value="commands"),
            ])
    async def reload(self, interaction: discord.Interaction, part: app_commands.Choice[str]):
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

    config = app_commands.Group(
        name='config', 
        description='Configuration commands', 
        allowed_installs=discord.app_commands.AppInstallationType(guild=True, user=False), 
        allowed_contexts=discord.app_commands.AppCommandContext(guild=True, dm_channel=False, private_channel=False),
        default_permissions=discord.Permissions(administrator=True)
    )

    @config.command(name="modules", description="Changes bot module config.")
    @app_commands.choices(module=modules)
    async def config_modules(self, interaction: discord.Interaction, module: app_commands.Choice[str], value: bool):
        config = functions.load_json(f"config/{self.client.main_name}/{interaction.guild.id}")
        if(config["Modules"][module.value] != value):
            config["Modules"][module.value] = value
            functions.save_json(config, f"config/{self.client.main_name}/{interaction.guild.id}")
            await interaction.response.send_message(f"Value of {module.name} set to {value}", ephemeral=True)
        else:
            await interaction.response.send_message(f"{module.name} already has that value", ephemeral=True)

    @app_commands.command(name="update", description="Pulls the latest code from the repository. Can only be used by the bot's owner.")
    @app_commands.check(is_owner)
    async def update(self, interaction: discord.Interaction):
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
        embed = discord.Embed(title="Bot Command Guide", description="Here's a list of available commands and features:", color=discord.Color.green())

        # General Commands
        embed.add_field(name="General Commands", value="---", inline=False)
        embed.add_field(name="/help", value="Displays this help message.", inline=True)
        embed.add_field(name="/tags `[user]`", value="Sends the Danbooru tag group wiki link. Optionally tags a `user`.", inline=True)

        # AI Commands
        embed.add_field(name="AI Commands", value="---", inline=False)
        embed.add_field(name="/message `<msg>` `[img]`", value="Send a message to the AI. Optionally attach an `img`.", inline=True)
        embed.add_field(name="AI Chat", value="Mention the bot or reply to its messages to chat with the AI. It considers message history for context.", inline=True)
        embed.add_field(name="AI Welcome/Goodbye", value="Automatic AI-generated messages when a member joins or leaves (if enabled).", inline=True)

        # Voice Commands
        embed.add_field(name="Voice Commands", value="---", inline=False)
        embed.add_field(name="/join", value="Joins the voice channel you are currently in.", inline=True)
        embed.add_field(name="/leave", value="Leaves the voice channel the bot is currently in.", inline=True)
        embed.add_field(name="/tts `<message>`", value="AI-based text-to-speech in the current voice channel. You can also use `~<message>`, without needing a command, for quick TTS.", inline=True)

        # Admin/Owner Commands
        embed.add_field(name="Moderation & Bot Management (Restricted)", value="---", inline=False)
        embed.add_field(name="/config modules `<module>` `<value>`", value="Enable or disable bot modules (Admin only).", inline=True)
        embed.add_field(name="/reload `<part>`", value="Reloads bot cogs or commands (Owner only).", inline=True)
        embed.add_field(name="/update", value="Pulls the latest code and updates dependencies (Owner only).", inline=True)

        embed.set_footer(text="Use commands by typing '/' in the chat.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(client):
    await client.add_cog(Commands(client))