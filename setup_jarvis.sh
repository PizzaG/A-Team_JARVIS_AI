#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
VENV="$ROOT/venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

log(){ echo; echo "==> $*"; }
die(){ echo "ERROR: $*" >&2; exit 1; }
ask_yn(){
  local prompt="$1" default="${2:-Y}" ans
  if [[ "$default" == "Y" ]]; then
    read -r -p "$prompt [Y/n] " ans
    ans="${ans:-Y}"
  else
    read -r -p "$prompt [y/N] " ans
    ans="${ans:-N}"
  fi
  [[ "$ans" =~ ^[Yy]$ ]]
}

command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "python3 was not found."
command -v curl >/dev/null 2>&1 || die "curl is required."

echo
echo "=============================================="
echo " JARVIS LOCAL SETUP"
echo "=============================================="
echo "Choose the features you want. You can rerun this setup later."
echo

VOICE=false
VISUALS=false
HANDS=false
MEMORY=true
INTERNET=true

ask_yn "Install voice input/output (Whisper + Kokoro)?" Y && VOICE=true
ask_yn "Install the AI visualizer?" Y && VISUALS=true
if $VISUALS; then
  ask_yn "Enable Barehands?" Y && HANDS=true
fi
ask_yn "Enable persistent Memory Vault?" Y || MEMORY=false
ask_yn "Enable Internet/web tools?" Y || INTERNET=false

FACE="board"
if $VISUALS; then
  mapfile -t FACES < <(find "$ROOT/ai-visualizer/faces" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort)
  echo
  echo "Available faces:"
  i=1
  for face in "${FACES[@]}"; do
    echo "  $i) $face"
    ((i++))
  done
  if ((${#FACES[@]})); then
    read -r -p "Choose face [1]: " choice
    choice="${choice:-1}"
    if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#FACES[@]} )); then
      FACE="${FACES[$((choice-1))]}"
    else
      echo "Invalid choice; using board."
    fi
  fi
fi

MODEL="qwen3.6:27b"
read -r -p "Ollama model [$MODEL]: " answer
MODEL="${answer:-$MODEL}"

# Native packages are needed only for voice.
install_system_deps(){
  local SUDO=""
  if [[ $EUID -ne 0 ]]; then
    command -v sudo >/dev/null 2>&1 || die "sudo is required to install system packages."
    SUDO="sudo"
  fi
  if command -v apt-get >/dev/null 2>&1; then
    log "Installing Linux dependencies for voice"
    $SUDO apt-get update
    $SUDO apt-get install -y python3-venv python3-dev build-essential curl ca-certificates espeak-ng libportaudio2 portaudio19-dev libsndfile1 libx11-6 libxext6 libxfixes3
  elif command -v pacman >/dev/null 2>&1; then
    log "Installing Linux dependencies for voice"
    $SUDO pacman -Sy --needed --noconfirm python python-pip base-devel curl ca-certificates espeak-ng portaudio libsndfile libx11 libxext libxfixes
  else
    echo "WARNING: Unsupported package manager. Install Python venv support manually."
    $VOICE && echo "         Also install PortAudio, libsndfile, and espeak-ng."
  fi
}

if ! "$PYTHON_BIN" -c 'import venv' >/dev/null 2>&1; then
  install_system_deps
fi
if $VOICE && ! command -v espeak-ng >/dev/null 2>&1; then
  install_system_deps
fi

if [[ ! -d "$VENV" ]]; then
  log "Creating Python virtual environment"
  "$PYTHON_BIN" -m venv "$VENV" || { install_system_deps; "$PYTHON_BIN" -m venv "$VENV"; }
else
  log "Existing venv found — reusing it"
fi
source "$VENV/bin/activate"
python -m pip install --upgrade pip setuptools wheel

log "Installing selected Python features"
python -m pip install -r "$ROOT/requirements/requirements-core.txt"
$VOICE && python -m pip install -r "$ROOT/requirements/requirements-voice.txt"
$INTERNET && python -m pip install -r "$ROOT/requirements/requirements-web.txt"

# Write the feature selections without touching unrelated configuration.
python - "$ROOT/config/jarvis.json" "$MODEL" "$VOICE" "$VISUALS" "$HANDS" "$MEMORY" "$INTERNET" "$FACE" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
cfg = json.loads(path.read_text()) if path.exists() else {}
cfg.setdefault("name", "JARVIS")
cfg.setdefault("ollama", {})
cfg["ollama"]["model"] = sys.argv[2]
cfg.setdefault("voice", {})
cfg["voice"]["enabled"] = sys.argv[3].lower() == "true"
cfg.setdefault("visuals", {})
cfg["visuals"]["enabled"] = sys.argv[4].lower() == "true"
cfg["visuals"]["barehands_enabled"] = sys.argv[5].lower() == "true"
cfg["visuals"]["face"] = sys.argv[8]
cfg.setdefault("memory", {})
cfg["memory"]["enabled"] = sys.argv[6].lower() == "true"
cfg.setdefault("research", {})
cfg["research"]["internet"] = sys.argv[7].lower() == "true"
cfg.setdefault("display", {})
cfg["display"].setdefault("show_tool_activity", False)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(cfg, indent=2) + "\n")
PY

# Check Ollama and offer to pull the selected model.
OLLAMA_URL="${OLLAMA_API_BASE:-http://127.0.0.1:11434}"
if curl -fsS "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
  echo "  OK  Ollama is reachable at $OLLAMA_URL"
else
  echo "WARNING: Ollama is not currently reachable at $OLLAMA_URL"
  if command -v ollama >/dev/null 2>&1; then
    if ask_yn "Start Ollama now?" Y; then
      nohup ollama serve > "$ROOT/ollama.log" 2>&1 &
      for _ in {1..30}; do
        curl -fsS "$OLLAMA_URL/api/tags" >/dev/null 2>&1 && break
        sleep 1
      done
    fi
  else
    echo "Install Ollama separately, then rerun setup."
  fi
fi

if command -v ollama >/dev/null 2>&1 && curl -fsS "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
  if ollama list | awk 'NR>1 {print $1}' | grep -Fxq "$MODEL"; then
    echo "  OK  Ollama model $MODEL is installed"
  else
    echo "Model $MODEL is not installed."
    if ask_yn "Pull $MODEL now?" Y; then
      ollama pull "$MODEL"
    else
      echo "WARNING: Jarvis cannot use $MODEL until it is installed."
    fi
  fi
fi

chmod +x "$ROOT/wake_jarvis.sh" "$ROOT/jarvis.py" "$ROOT/setup_jarvis.sh" "$ROOT/setup.sh" 2>/dev/null || true

log "Setup complete"
echo "  Model      : $MODEL"
echo "  Voice      : $VOICE"
echo "  Visualizer : $VISUALS"
echo "  Face       : $FACE"
echo "  Barehands  : $HANDS"
echo "  Memory     : $MEMORY"
echo "  Internet   : $INTERNET"
echo
echo "Start with: $ROOT/wake_jarvis.sh"
echo
echo "Jarvis Setup Complete"
echo 
echo "Press ENTER To Exit"
