#!/usr/bin/env bash

here="$HOME/.config/my-shell"
. ./.venv/bin/activate
. "$here/workflows/shared.sh"
python "$here/init.py"
pkill $app_name
uwsm app -- python "$here/app.py" >/dev/null 2>&1 &
disown

# Run update script
bash "$here/workflows/update.sh"
