import subprocess
import threading
from scripts.functions import load_json


variables = load_json("general")

def run_script(bot_name):
    subprocess.run(f"bot-env\Scripts\python.exe bot.py {bot_name}")

botThreads = []

if __name__ == "__main__":
    for bot in variables["Bots"]:
        botThread = threading.Thread(target=run_script, args=(bot,))
        botThreads.append(botThread)
        botThread.start()
    
    for thread in botThreads:
        thread.join()
