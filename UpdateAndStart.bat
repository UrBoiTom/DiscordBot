@echo off
git pull
if not exist "bot-env\" python3 -m venv bot-env
call bot-env\Scripts\activate.bat
pip install -U -r requirements.txt
py bot.py
pause