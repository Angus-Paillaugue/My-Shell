#!/usr/bin/env bash

here="$HOME/.config/vellum-shell"
source $here/.venv/bin/activate
. "$here/workflows/shared.sh"

pkill $app_name_lower
pkill -f vellum-shell-phonebridge-server
python "$here/init.py"
init_status=$?
# If the init was not successful, exit
if [[ $init_status -ne 0 ]]; then
  echo "Exiting."
  exit $init_status
fi
# Launch shell
uwsm app -- python "$here/app.py" >/dev/null 2>&1 &
disown
# Launch phone pairing server
uwsm app -- python -m mobile.server.app >/dev/null 2>&1 &
disown

# Run update script
sleep 2
bash "$here/workflows/update.sh"
