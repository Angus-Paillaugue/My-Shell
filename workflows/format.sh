#!/usr/bin/env bash

requiredCommands=("yapf" "prettier" "shfmt")

here=$(dirname "$(readlink -f "$0")")
projectRoot=$(realpath "$here/..")
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
	yapf -r --style google --verbose -i .
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
