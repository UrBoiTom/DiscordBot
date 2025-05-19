This fork includes several Linux- and development-friendly updates to improve cross-platform support.

Changes Made:

Converted UpdateAndStart.bat into run.sh for Linux compatibility.

Usage: chmod +x run.sh && ./run.sh

This script auto-pulls updates from the repo and launches the bot via Python.


Edited bots.py to support Linux execution:

Replaced hardcoded python.exe path with dynamic Python path using:

import os  
os.system(f"{sys.executable} bot.py")


