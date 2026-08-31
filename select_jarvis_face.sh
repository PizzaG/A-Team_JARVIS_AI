#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/config/jarvis.json"
FACES_DIR="$SCRIPT_DIR/ai-visualizer/faces"

if [[ ! -f "$CONFIG" ]]; then
    echo "Error: $CONFIG not found."
    exit 1
fi

if [[ ! -d "$FACES_DIR" ]]; then
    echo "Error: $FACES_DIR not found."
    exit 1
fi

# Read current face without requiring a JSON parser.
current_face="$(grep -oE '"face"[[:space:]]*:[[:space:]]*"[^"]+"' "$CONFIG" \
    | head -n1 \
    | sed -E 's/.*"face"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')"

[[ -n "$current_face" ]] || current_face="board"

# Discover available faces.
mapfile -t faces < <(
    find "$FACES_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' \
    | sort
)

if [[ ${#faces[@]} -eq 0 ]]; then
    echo "No Faces Found."
    exit 1
fi

echo
echo "JARVIS Face Selector"
echo "===================="
echo "Current Face: ${current_face^}"
echo

for i in "${!faces[@]}"; do
    marker=""
    [[ "${faces[$i]}" == "$current_face" ]] && marker=" (current)"
    printf "%d) %s%s\n" "$((i + 1))" "${faces[$i]}" "$marker"
done

echo
read -r -p "Select Face: " choice

if [[ -z "$choice" ]]; then
    echo "No Changes Made."
    exit 0
fi

if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
    echo "Invalid Selection. No Changes Made."
    exit 1
fi

index=$((choice - 1))

if (( index < 0 || index >= ${#faces[@]} )); then
    echo "Invalid Selection. No Changes Made."
    exit 1
fi

selected="${faces[$index]}"

# Replace only the visuals.face value.
sed -i -E \
    "0,/\"face\"[[:space:]]*:[[:space:]]*\"[^\"]*\"/s//\"face\": \"$selected\"/" \
    "$CONFIG"

echo
echo "Face Set To: $selected"
echo
echo "Press ENTER To Exit"
read
