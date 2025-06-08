#!/usr/bin/env bash

here=$(dirname "$(readlink -f "$0")")
projectRoot=$(realpath "$here/..")

source "$projectRoot/.venv/bin/activate"
DEV_MODE=true python "$projectRoot/app.py" "$@"
