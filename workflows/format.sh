#!/usr/bin/env bash

requiredCommands=("black" "prettier" "shfmt")

here=$(dirname "$(readlink -f "$0")")
# Project root is one level up from the script directory
projectRoot=$(dirname "$here")
cd "$projectRoot" || exit 1

checkCommands() {
	for cmd in "${requiredCommands[@]}"; do
		if ! command -v "$cmd" &>/dev/null; then
			echo "Error: $cmd is not installed."
			exit 1
		fi
	done
}

formatPython() {
	echo "Formatting Python files..."
	black .
}

formatCSS() {
	ignorePatterns=("config/")
	echo "Formatting CSS files..."
	prettier --write "**/*.css" --ignore-path <(printf "%s\n" "${ignorePatterns[@]}")
}

formatShell() {
	echo "Formatting shell scripts..."
	shfmt -w .
}

formatAll() {
	formatPython
	formatCSS
	formatShell
}

main() {
	checkCommands
	formatAll
	echo "All files formatted successfully."
}

main "$@"
