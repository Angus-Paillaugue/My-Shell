#!/usr/bin/env bash

here="$HOME/.config/my-shell"
source $here/.venv/bin/activate
. "$here/workflows/shared.sh"

pkill $app_name_lower
python "$here/init.py"
init_status=$?
# If the init was not successful, exit
if [[ $init_status -ne 0 ]]; then
  echo "Exiting."
  exit $init_status
fi
uwsm app -- python "$here/app.py" >/dev/null 2>&1 &
disown

# Run update script
sleep 2
bash "$here/workflows/update.sh"
