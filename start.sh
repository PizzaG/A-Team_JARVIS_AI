#!/bin/bash
# fullstack-agent: Local AI Agent with Memory, Voice, Face, and Hands.
# Copyright (C) 2026 Jared Rhodenizer, local AI edition.
# SPDX-License-Identifier: AGPL-3.0-or-later

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

echo "========================================================="
echo "  JARVIS - FULLSTACK LOCAL AI AGENT (Ollama Edition)"
echo "========================================================="
echo

# Check Ollama
if ! curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "[WARNING] Ollama does not appear to be running at http://127.0.0.1:11434!"
  echo "          Please start Ollama (e.g. run 'ollama serve' or open Ollama app)."
  echo
else
  echo "[OK] Ollama local inference backend detected."
fi

# Ensure memory vault
python3 vault_manager.py >/dev/null 2>&1

MODE="${1:-all}"
PIDS=()

cleanup() {
  trap - EXIT INT TERM
  for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null; done
  echo
  echo "Agent stopped."
}
trap cleanup EXIT INT TERM

if [ -d "ai-visualizer" ] && [ "$MODE" != "hands" ]; then
  (cd ai-visualizer && exec python3 server.py) &
  PIDS+=($!)
  echo "[1/2] Web Dashboard & Air Board started (opening in your browser at http://127.0.0.1:8790/)"
fi

if [ -d "backtalk" ] && [ "$MODE" != "web" ]; then
  echo "[2/2] Voice engine starting in this terminal. Hold your talk key to speak; Ctrl-C stops everything."
  cd backtalk && exec uv run python3 -m backtalk.main
else
  echo "Unified server running at http://127.0.0.1:8790/. Press Ctrl-C to stop."
  wait
fi
