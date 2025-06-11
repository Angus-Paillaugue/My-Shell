#!/usr/bin/env bash

# Variables
app_name="My-Shell"
app_name_lower=$(echo "$app_name" | tr '[:upper:]' '[:lower:]')
project_dir="$HOME/.config/my-shell"
release_branch="main"

get_latest_version() {
  local latest_version
  latest_version=$(curl -s "https://raw.githubusercontent.com/Angus-Paillaugue/$app_name/refs/heads/$release_branch/VERSION")
  strip_latest_version="$(echo "$latest_version" | grep -Eo '^[0-9]+\.[0-9]+\.[0-9]+')"
  echo "$strip_latest_version"
}

get_local_version() {
  local local_version
  file_path="$project_dir/VERSION"
  if [[ -f "$file_path" ]]; then
    local_version=$(cat "$file_path")
  else
    local_version="0.0.0" # Default version if file does not exist
  fi
  echo "$local_version"
}

check_if_new_version() {
  latest_version=$(get_latest_version)
  local_version=$(get_local_version)

  if [[ -n "$latest_version" && -n "$local_version" && "$latest_version" != "$local_version" ]]; then
    echo $latest_version
    return 0
  else
    echo "You are already on the latest version: $local_version"
    return 1
  fi
}
