#!/usr/bin/env bash

requiredCommands=("yapf" "prettier" "shfmt")

projectRoot="$HOME/.config/my-shell"
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
  prettier --write "**/*.css"
}

formatShell() {
  echo "Formatting shell scripts..."
  shfmt -i=2 -w .
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
