#!/usr/bin/env bash

here=$(dirname "$(readlink -f "$0")")
project_dir=$(realpath "$here/..")
. "$project_dir/workflows/shared.sh"

current_local_version=$(get_local_version)
current_latest_version=$(get_latest_version)

if [[ -z "$current_latest_version" ]]; then
    echo "Error: Unable to fetch the latest version."
    exit 1
fi

if [[ -z "$current_local_version" ]]; then
    echo "Error: Local version file not found."
    exit 1
fi

update_versions_in_files() {
    local new_version="$1"

    echo "$new_version" > "$project_dir/VERSION"
    poetry version "$new_version"
}

main() {
  local new_version
  read -p "Enter the new version (current: $current_local_version, latest: $current_latest_version): " new_version
  if [[ -z "$new_version" ]]; then
      echo "No version entered. Exiting."
      exit 0
  fi
  if [[ "$new_version" == "$current_local_version" ]]; then
      echo "The new version is the same as the current version. No changes made."
      exit 0
  fi
  if ! [[ "$new_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      echo "Invalid version format. Please use semantic versioning (e.g., 1.0.0)."
      exit 1
  fi
  update_versions_in_files "$new_version"
}

main "$@"
