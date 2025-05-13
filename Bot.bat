@echo off
call bot-env\Scripts\activate.bat
bot-env\Scripts\python.exe bot.py %*
pause