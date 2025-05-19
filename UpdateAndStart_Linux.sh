#!/bin/bash
chmod +x Start_Linux.sh
git pull --rebase --autostash

if [ ! -d "bot-env" ]; then
  python3 -m venv bot-env
fi

source bot-env/bin/activate
pip install -U -r requirements.txt
python3 bots.py