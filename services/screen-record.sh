#!/bin/env bash

# Check if XDG_VIDEOS_DIR is not set
if [ -z "$XDG_VIDEOS_DIR" ]; then
  XDG_VIDEOS_DIR="$HOME/Videos"
fi

SAVE_DIR="$XDG_VIDEOS_DIR/Recordings"
mkdir -p "$SAVE_DIR"

if pgrep -f "gpu-screen-recorder" >/dev/null; then
  pkill -SIGINT -f "gpu-screen-recorder"

  sleep 1

  LAST_VIDEO=$(ls -t "$SAVE_DIR"/*.mp4 2>/dev/null | head -n 1)

  ACTION=$(notify-send -a "Screen-recorder" "⬜ Recording stopped" \
    -A "view=View" -A "open=Open folder")

  if [ "$ACTION" = "view" ] && [ -n "$LAST_VIDEO" ]; then
    xdg-open "$LAST_VIDEO"
  elif [ "$ACTION" = "open" ]; then
    xdg-open "$SAVE_DIR"
  fi
  exit 0
fi

OUTPUT_FILE="$SAVE_DIR/$(date +%Y-%m-%d-%H-%M-%S).mp4"

notify-send -a "Screen-recorder" "🔴 Recording started"
gpu-screen-recorder -w screen -q ultra -a default_output -ac opus -cr full -f 60 -o "$OUTPUT_FILE"
