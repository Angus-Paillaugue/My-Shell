#!/usr/bin/env bash

requiredCommands=("yapf" "prettier" "shfmt" "isort")

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
  isort **/*.py
}

formatCSS() {
  echo "Formatting CSS files (preserving {{VARIABLES}})..."

  for file in $(find "$projectRoot/styles" -type f -name "*.mcss"); do
    tmp="${file}.tmp"

    # Step 1: replace {{...}} with placeholders
    perl -0777 -pe 's/\{\{(.*?)\}\}/__PLACEHOLDER__(\1)__PLACEHOLDER__/sg' "$file" >"$tmp"

    # Step 2: run prettier on the temporary file
    prettier --parser css --write "$tmp" >/dev/null 2>&1

    # Step 3: restore placeholders back to {{...}}, even if Prettier added spaces or line breaks
    perl -0777 -pe 's/__PLACEHOLDER__\s*\(\s*(.*?)\s*\)\s*__PLACEHOLDER__/{{\1}}/sg' "$tmp" >"$file"

    rm -f "$tmp"
    echo "→ $file formatted"
  done
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
