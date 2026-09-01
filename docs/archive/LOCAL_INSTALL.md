# Local Jarvis
This build removes the Claude dependency from the voice loop.

## Stack
- Brain: Ollama + qwen3.8:27b
- Ears: faster-whisper (local)
- Mouth: Kokoro (local)
- Face: Jared Rhodenizer's ai-visualizer
- Hands: Jared Rhodenizer's barehands
- Optional coding agent: Aider

## Fresh setup
```bash
cd ~/local-jarvis
chmod +x setup_jarvis.sh wake_jarvis.sh
./setup_jarvis.sh
./wake_jarvis.sh
```

The virtual environment is intentionally not included in the ZIP. `setup_jarvis.sh` creates it and installs `requirements-local.txt`.

The launcher starts the two local visual servers, waits for them to become ready, opens the board face when `xdg-open` is available, then starts Jarvis.

Press and hold **F4**, speak, and release F4.

## Local research
Jarvis now has a read-only research toolset. The default research root is the `local-jarvis` folder itself and can be changed in `config/jarvis.json`:

```json
"research": {
  "root": ".",
  "max_results": 50
}
```

The research tools can list files, search text/code/config files, read files with line numbers, and inspect file metadata. Paths are sandboxed to the configured research root. Large/binary files are not loaded as text; use an appropriate extractor in a later tool phase.
