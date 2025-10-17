#!/bin/env bash

here="$HOME/.config/my-shell"
source $here/.venv/bin/activate
. "$here/workflows/shared.sh"

cd "$here" || exit 1
pkill -f "$app_name_lower-settings"
export GTK_DEBUG=null
uwsm app -- python "modules/settings.py" > /dev/null 2>&1 &
