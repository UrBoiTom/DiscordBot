@echo off
git pull --rebase --autostash
if not exist "bot-env\" python3 -m venv bot-env
call bot-env\Scripts\activate.bat
pip install -U -r requirements.txt
bot-env\Scripts\python.exe bots.py