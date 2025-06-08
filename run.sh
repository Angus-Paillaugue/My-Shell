#!/usr/bin/env bash

cd ~/.config/my-shell/
source ./.venv/bin/activate
python ./init.py
uwsm app -- python ./app.py >/dev/null 2>&1 &
disown

# Run update script
bash ./workflows/update.sh
