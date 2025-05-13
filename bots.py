import os
import sys
import subprocess
from scripts.functions import load_json

variables = load_json("general")

for bot in variables["Bots"]:
    os.system(f"start cmd.exe /c Bot.bat {bot}")