#!/usr/bin/env bash

# Variables
release_branch="main"
here=$(dirname "$(readlink -f "$0")")
project_dir=$(realpath "$here/..")
app_name=$(cat $project_dir/services/config.py | grep -E "^APP_NAME\s*=" | sed -E "s/^APP_NAME\s*=\s*['\"]?([^'\"]+)['\"]?/\1/")
notification_app_name="󰚰 $app_name Updater"

get_latest_version() {
	local latest_version
	latest_version=$(curl -s "https://raw.githubusercontent.com/Angus-Paillaugue/My-Shell/refs/heads/$release_branch/VERSION")
	echo "$latest_version"
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

update_version() {
	git fetch origin "$release_branch" &&
		git checkout "$release_branch" &&
		git pull origin "$release_branch"

	if [[ $? -eq 0 ]]; then
		notify-send -a "$notification_app_name" "Successfully updated to version: $latest_version"
	else
		notify-send -a "$notification_app_name" "Update failed. Please check the logs for more details."
	fi
}

main() {
	if check_if_new_version; then
		ACTION=$(notify-send -a "$notification_app_name" "A new version of $app_name is available ($local_version -> $latest_version)" -A "dismiss=Dismiss" -A "update=Update")

		if [ "$ACTION" = "update" ]; then
			update_version
		elif [ "$ACTION" = "dismiss" ]; then
			echo "Dismissing..."
		fi
	else
		echo "No updates available."
	fi
}

# Run the main function
main "$@"
