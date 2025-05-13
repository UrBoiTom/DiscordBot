import os
import sys
import subprocess
from scripts.functions import load_json

keys = load_json("keys")

for bot in keys["Bots"]:
    os.system(f"start cmd.exe /c StartBot.bat {bot}")