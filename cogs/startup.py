from discord.ext import commands
import os
import copy
import shutil
import scripts.functions as functions
functions.reload(functions)

class startup(commands.Cog):
    def __init__(self, client):
        self.client = client


        for guild in self.client.guilds:
            if not f"{str(guild.id)}.json" in os.listdir(os.path.join("config", self.client.main_name)):
                source_path = os.path.join("config", "default_config.json")
                destination_path = os.path.join("config", self.client.main_name, f"{str(guild.id)}.json")
                shutil.copy2(source_path, destination_path)

        current_guild_files = [f"{str(guild.id)}.json" for guild in self.client.guilds]
        for file in os.listdir(os.path.join("config", self.client.main_name)):
            if file.endswith(".json"):
                full_config_file_path = os.path.join("config", self.client.main_name, file)
                if file not in current_guild_files:
                    os.remove(full_config_file_path)

        def refresh_files(default_config, config_dir):
            if not os.path.exists(config_dir):
                os.mkdir(config_dir)
            for file in os.listdir(config_dir):
                if file.endswith(".json"):
                    full_config_file_path = os.path.join(config_dir, file)
                    path_for_json_func = os.path.join(config_dir, file.removesuffix(".json"))

                    current_guild_config_data = functions.load_json(path_for_json_func)

                    if not isinstance(current_guild_config_data, dict):
                        print(f"Warning: Data in {full_config_file_path} is not a dictionary. Rebuilding with default structure.")
                        current_guild_config_data = {} # Treat as empty to ensure it's rebuilt

                    def merge_configs_recursive(template_dict, data_dict):
                        merged = {}
                        for key, template_value in template_dict.items():
                            if isinstance(template_value, dict):
                                data_value_for_key = data_dict.get(key)
                                if isinstance(data_value_for_key, dict):
                                    merged[key] = merge_configs_recursive(template_value, data_value_for_key)
                                else:
                                    merged[key] = copy.deepcopy(template_value) # Use default sub-dict
                            elif key in data_dict:
                                merged[key] = data_dict.get(key) # Use value from current config
                            else:
                                merged[key] = copy.deepcopy(template_value) # Key missing in current, use default
                        return merged

                    updated_guild_config = merge_configs_recursive(default_config, current_guild_config_data)

                    if updated_guild_config != current_guild_config_data:
                        functions.save_json(updated_guild_config, path_for_json_func)
                        print(f"Config for {file} in {config_dir} updated to match default structure.")

        refresh_files(functions.load_json("config/default_config"), os.path.join("config", self.client.main_name))
        refresh_files(functions.load_json("config/default_voice"), os.path.join("config", "voice"))
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if not f"{str(guild.id)}.json" in os.listdir(os.path.join("config", self.client.main_name)):
                source_path = os.path.join("config", "default_config.json")
                destination_path = os.path.join("config", self.client.main_name, f"{str(guild.id)}.json")
                shutil.copy2(source_path, destination_path)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        if(os.path.exists(os.path.join("config", self.client.main_name, f"{str(guild.id)}.json"))):
            os.remove(os.path.join("config", self.client.main_name, f"{str(guild.id)}.json"))

async def setup(client):
    await client.add_cog(startup(client))