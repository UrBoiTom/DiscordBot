@echo off
if not exist "bot-env\" python3 -m venv bot-env
bot-env\Scripts\activate.bat
pip install -U -r requirements.txt