#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -d "$ROOT/venv" ]]; then
    echo "ERROR: $ROOT/venv does not exist."
    echo "Create it with: python3 -m venv venv"
    exit 1
fi

PYTHON="$ROOT/venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
    echo "ERROR: venv Python was not found."
    echo "Expected: $PYTHON"
    exit 1
fi

source "$ROOT/venv/bin/activate"

# Keep the local environment in sync with the selected features.
# Core is always installed; optional dependencies follow jarvis.json.
"$PYTHON" -m pip install --disable-pip-version-check -q -r "$ROOT/requirements/requirements-core.txt"

VOICE_ENABLED="$("$PYTHON" -c 'import json; c=json.load(open("config/jarvis.json")); print(str(c.get("voice",{}).get("enabled",True)).lower())')"

INTERNET_ENABLED="$("$PYTHON" -c 'import json; c=json.load(open("config/jarvis.json")); print(str(c.get("research",{}).get("internet",True)).lower())')"

if [[ "$VOICE_ENABLED" == "true" ]]; then
    echo "Installing Voice Dependencies ..."
    "$PYTHON" -m pip install --disable-pip-version-check -q -r "$ROOT/requirements/requirements-voice.txt"
fi
if [[ "$INTERNET_ENABLED" == "true" ]]; then
    echo "Installing Web Dependencies ..."
    "$PYTHON" -m pip install --disable-pip-version-check -q -r "$ROOT/requirements/requirements-web.txt"
fi

export HSA_OVERRIDE_GFX_VERSION="${HSA_OVERRIDE_GFX_VERSION:-11.0.2}"
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
export OLLAMA_API_BASE="${OLLAMA_API_BASE:-http://127.0.0.1:11434}"
export PYTHONWARNINGS="${PYTHONWARNINGS:-ignore}"

mkdir -p "$ROOT/ai-visualizer" "$ROOT/barehands/state" "$ROOT/config"

printf 'idle' > "$ROOT/ai-visualizer/.voice_state"
printf 'idle' > "$ROOT/barehands/state/state"

rm -f \
    "$ROOT/ai-visualizer/.voice_waveform" \
    "$ROOT/barehands/state/wave.json"

# Ollama is normally already a system/user service.
# Only start one if needed.
OLLAMA_PID=""

if ! curl -fsS "$OLLAMA_API_BASE/api/tags" >/dev/null 2>&1; then
    echo "Starting Ollama..."
    nohup ollama serve > "$ROOT/logs/ollama.log" 2>&1 &
    OLLAMA_PID=$!
    for _ in {1..30}; do
        curl -fsS "$OLLAMA_API_BASE/api/tags" >/dev/null 2>&1 && break
        sleep 1
    done
fi

# Read optional visual features from configuration.
VISUALS_ENABLED="$("$PYTHON" -c 'import json; c=json.load(open("config/jarvis.json")); print(str(c.get("visuals",{}).get("enabled",True)).lower())')"

HANDS_ENABLED="$("$PYTHON" -c 'import json; c=json.load(open("config/jarvis.json")); print(str(c.get("visuals",{}).get("barehands_enabled",True)).lower())')"

FACE_NAME="$("$PYTHON" -c 'import json; c=json.load(open("config/jarvis.json")); print(c.get("visuals",{}).get("face","board"))')"

FACE_DIR="$ROOT/ai-visualizer/faces/$FACE_NAME"

if [[ ! -d "$FACE_DIR" ]]; then
    echo "WARNING: configured face '$FACE_NAME' was not found; using 'board'."
    FACE_NAME="board"
fi

FACE_URL="http://127.0.0.1:8790/faces/$FACE_NAME/"
HANDS_URL="http://127.0.0.1:8794/stage.html"

export FACE_URL
export HANDS_URL

if [[ "$VISUALS_ENABLED" == "true" ]]; then
    echo "Starting AI Visualizer (${FACE_NAME^}) ..."
    if ! curl -fsS http://127.0.0.1:8790/state >/dev/null 2>&1; then
        (
            cd "$ROOT/ai-visualizer"
            exec "$PYTHON" server.py --no-open
        ) > "$ROOT/logs/faces.log" 2>&1 &
        FACE_PID=$!
    else
        FACE_PID=""
    fi
    for _ in {1..30}; do
        if curl -fsS http://127.0.0.1:8790/state >/dev/null 2>&1; then
            break
        fi
        sleep 0.2
    done
    if command -v xdg-open >/dev/null 2>&1; then
        (
            sleep 0.5
            xdg-open "$FACE_URL" >/dev/null 2>&1
        ) &
    fi
else
    echo "AI Visualizer Disabled."
    FACE_PID=""
fi

if [[ "$HANDS_ENABLED" == "true" ]]; then
    echo "Starting Barehands ..."
    if ! curl -fsS http://127.0.0.1:8794/orb >/dev/null 2>&1; then
        (
            cd "$ROOT/barehands"
            exec "$PYTHON" server.py
        ) > "$ROOT/logs/barehands.log" 2>&1 &
        HANDS_PID=$!
    else
        HANDS_PID=""
    fi
    for _ in {1..30}; do
        if curl -fsS http://127.0.0.1:8794/orb >/dev/null 2>&1; then
            break
        fi
        sleep 0.2
    done
else
    echo "Barehands Disabled."
    HANDS_PID=""
fi

cleanup() {
    printf 'idle' > "$ROOT/ai-visualizer/.voice_state" || true
    printf 'idle' > "$ROOT/barehands/state/state" || true
    rm -f \
        "$ROOT/ai-visualizer/.voice_waveform" \
        "$ROOT/barehands/state/wave.json" || true
    [[ -n "${FACE_PID:-}" ]] && \
        kill "$FACE_PID" 2>/dev/null || true

    [[ -n "${HANDS_PID:-}" ]] && \
        kill "$HANDS_PID" 2>/dev/null || true
    # Never pkill generic server.py processes and never kill
    # an Ollama service we did not start.
    [[ -n "${OLLAMA_PID:-}" ]] && \
        kill "$OLLAMA_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# echo
# echo "=============================================="
# echo " JARVIS LOCAL STACK"
# echo "=============================================="
# echo " Brain : Ollama / $(grep -o '"model"[[:space:]]*:[[:space:]]*"[^"]*"' "$ROOT/config/jarvis.json" | head -1 | sed -E 's/.*"([^"]+)"$/\1/')"
# echo " Voice : Whisper -> Kokoro"
# if [[ "$VISUALS_ENABLED" == "true" ]]; then
#     echo " Face Link  : $FACE_URL"
# else
#     echo " Face Link  : disabled"
# fi
# if [[ "$HANDS_ENABLED" == "true" ]]; then
#     echo " Hands Link : http://127.0.0.1:8794/stage.html"
# else
#     echo " Hands Link : disabled"
# fi
# echo " Talk  : hold F4"
# echo "=============================================="
# echo

"$PYTHON" "$ROOT/jarvis.py"
