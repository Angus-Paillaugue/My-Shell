#!/usr/bin/env bash

here=$(dirname "$(readlink -f "$0")")
project_dir=$(realpath "$here/..")
. "$project_dir/workflows/shared.sh"
app_name=$(cat $project_dir/services/config.py | grep -E "^APP_NAME\s*=" | sed -E "s/^APP_NAME\s*=\s*['\"]?([^'\"]+)['\"]?/\1/")
notification_app_name="󰚰 $app_name Updater"

update_version() {
  git fetch origin "$release_branch" &&
    git checkout "$release_branch" &&
    git pull origin "$release_branch"

  if [[ $? -eq 0 ]]; then
    notify-send -a "$notification_app_name" "Successfully updated to version: $latest_version"
    echo "Update successful. Restarting the application..."
    . "$project_dir/run.sh"
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

main "$@"
