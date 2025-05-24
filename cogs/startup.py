from discord.ext import commands
import os
import scripts.functions as functions
functions.reload(functions)

class startup(commands.Cog):
    def __init__(self, client):
        self.client = client

        if not self.client.main_name in os.listdir("config"):
            os.mkdir(os.path.join("config", self.client.main_name))

        current_guild_files = [f"{str(guild.id)}.json" for guild in self.client.guilds]
        for file in os.listdir(os.path.join("config", self.client.main_name)):
            if file.endswith(".json"):
                if not file in current_guild_files:
                    os.remove(os.path.join("config", self.client.main_name, file))

        for guild in self.client.guilds:
            if not f"{str(guild.id)}.json" in os.listdir(os.path.join("config", self.client.main_name)):
                os.popen(f'copy {os.path.join("config", "default_config.json")} {os.path.join("config", self.client.main_name, str(guild.id))}.json')
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if not f"{str(guild.id)}.json" in os.listdir(os.path.join("config", self.client.main_name)):
                os.popen(f'copy {os.path.join("config", "default_config.json")} {os.path.join("config", self.client.main_name, str(guild.id))}.json')

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        if(os.path.exists(os.path.join("config", self.client.main_name, f"{str(guild.id)}.json"))):
            os.remove(os.path.join("config", self.client.main_name, f"{str(guild.id)}.json"))

async def setup(client):
    await client.add_cog(startup(client))