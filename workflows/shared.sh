#!/usr/bin/env bash

# Variables
here=$(dirname "$(readlink -f "$0")")
project_dir=$(realpath "$here/..")
app_name=$(cat $project_dir/services/config.py | grep -E "^APP_NAME\s*=" | sed -E "s/^APP_NAME\s*=\s*['\"]?([^'\"]+)['\"]?/\1/")
release_branch="main"

get_latest_version() {
	local latest_version
	latest_version=$(curl -s "https://raw.githubusercontent.com/Angus-Paillaugue/My-Shell/refs/heads/$release_branch/VERSION")
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
