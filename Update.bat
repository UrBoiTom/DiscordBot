@echo off
git pull --rebase --autostash
call bot-env\Scripts\activate.bat
pip install -U -r requirements.txt