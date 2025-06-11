#!/usr/bin/env bash

here="$HOME/.config/my-shell"
. ./.venv/bin/activate
. "$here/workflows/shared.sh"

pkill $app_name_lower
python "$here/init.py"
uwsm app -- python "$here/app.py" >/dev/null 2>&1 &
disown

# Run update script
bash "$here/workflows/update.sh"
