#!/usr/bin/env bash

hyprpicker -a -n -f hex && sleep 0.1

if [ $? -ne 0 ]; then
  exit 1
fi
magick -size 64x64 xc:"$(wl-paste)" /tmp/color.png
notify-send -e "HEX color picked" "$(wl-paste)" -i /tmp/color.png -a "Hyprpicker"
rm /tmp/color.png
