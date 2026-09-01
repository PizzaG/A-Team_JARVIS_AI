# Kokoro Voice Selector

Run `./select_voice.sh` from the JARVIS directory.

The selector updates only the configured Kokoro voice in `config/jarvis.json`.
Press Enter to cancel.

Voice availability is discovered from the installed Kokoro package when the
installed package exposes voice metadata; otherwise the currently configured
voice is retained as the safe fallback.
