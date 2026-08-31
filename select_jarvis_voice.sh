#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/config/jarvis.json"

if [[ ! -f "$CONFIG" ]]; then
    echo "Error: $CONFIG not found."
    exit 1
fi

# Read current Kokoro voice.
current_voice="$(grep -oE '"kokoro_voice"[[:space:]]*:[[:space:]]*"[^"]+"' "$CONFIG" \
    | head -n1 \
    | sed -E 's/.*"kokoro_voice"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')"

[[ -n "$current_voice" ]] || current_voice="bm_lewis"

echo
echo "JARVIS Kokoro Voice Selector"
echo "============================"
echo

echo "Current Voice: $current_voice"
echo
echo "Voice Mode:"
echo "1) Single Voice"
echo "2) Dual Mixed Voice"
echo

echo "Voices:"
echo "American Female"
echo "---------------"
echo " 1) heart"
echo " 2) alloy"
echo " 3) aoede"
echo " 4) bella"
echo " 5) jessica"
echo " 6) kore"
echo " 7) nicole"
echo " 8) nova"
echo " 9) river"
echo "10) sarah"
echo "11) sky"
echo

echo "American Male"
echo "-------------"
echo "12) adam"
echo "13) echo"
echo "14) eric"
echo "15) fenrir"
echo "16) liam"
echo "17) michael"
echo "18) onyx"
echo "19) puck"
echo "20) santa"
echo

echo "British Female"
echo "--------------"
echo "21) alice"
echo "22) emma"
echo "23) isabella"
echo "24) lily"
echo

echo "British Male"
echo "------------"
echo "25) daniel"
echo "26) fable"
echo "27) george"
echo "28) lewis"
echo

read -r -p "Select Voice Mode: " mode

if [[ -z "$mode" ]]; then
    echo "No changes made."
    exit 0
fi

if [[ "$mode" != "1" && "$mode" != "2" ]]; then
    echo "Invalid selection. No changes made."
    exit 1
fi

get_voice() {
    case "$1" in
        1)  printf '%s' "af_heart" ;;
        2)  printf '%s' "af_alloy" ;;
        3)  printf '%s' "af_aoede" ;;
        4)  printf '%s' "af_bella" ;;
        5)  printf '%s' "af_jessica" ;;
        6)  printf '%s' "af_kore" ;;
        7)  printf '%s' "af_nicole" ;;
        8)  printf '%s' "af_nova" ;;
        9)  printf '%s' "af_river" ;;
        10) printf '%s' "af_sarah" ;;
        11) printf '%s' "af_sky" ;;
        12) printf '%s' "am_adam" ;;
        13) printf '%s' "am_echo" ;;
        14) printf '%s' "am_eric" ;;
        15) printf '%s' "am_fenrir" ;;
        16) printf '%s' "am_liam" ;;
        17) printf '%s' "am_michael" ;;
        18) printf '%s' "am_onyx" ;;
        19) printf '%s' "am_puck" ;;
        20) printf '%s' "am_santa" ;;
        21) printf '%s' "bf_alice" ;;
        22) printf '%s' "bf_emma" ;;
        23) printf '%s' "bf_isabella" ;;
        24) printf '%s' "bf_lily" ;;
        25) printf '%s' "bm_daniel" ;;
        26) printf '%s' "bm_fable" ;;
        27) printf '%s' "bm_george" ;;
        28) printf '%s' "bm_lewis" ;;
        *) return 1 ;;
    esac
}

choose_voice() {
    local prompt="$1"
    local choice
    local selected

    while true; do
        read -r -p "$prompt: " choice

        if [[ -z "$choice" ]]; then
            echo "No changes made." >&2
            exit 0
        fi

        if selected="$(get_voice "$choice")"; then
            printf '%s' "$selected"
            return 0
        fi

        echo "Invalid selection. Choose 1-28." >&2
    done
}

if [[ "$mode" == "1" ]]; then

    selected_voice="$(choose_voice "Select Voice")"
    final_voice="$selected_voice"

else

    first_voice="$(choose_voice "Select First Voice")"

    echo
    echo "First Voice: $first_voice"

    second_voice="$(choose_voice "Select Second Voice")"

    if [[ "$first_voice" == "$second_voice" ]]; then
        echo
        echo "Same voice selected twice."
        echo "Using it as a single voice."

        final_voice="$first_voice"
    else
        final_voice="${first_voice},${second_voice}"
    fi

fi

# Replace only the existing kokoro_voice value.
sed -i -E \
    "s|(\"kokoro_voice\"[[:space:]]*:[[:space:]]*\")[^\"]*(\")|\1${final_voice}\2|" \
    "$CONFIG"

echo
echo "Voice set to: $final_voice"
echo
echo "Press ENTER To Exit"
read
