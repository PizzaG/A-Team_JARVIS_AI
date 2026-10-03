# A-Team JARVIS AI

> A local-first desktop AI assistant built around Ollama/Qwen, with optional voice, visuals, hand tracking, persistent memory, and web research.

## What It Includes

- **JARVIS Agent** — Python runtime with local Ollama/Qwen inference; JARVIS is the default Agent Name and can be changed from the GUI
- **GTK3 Desktop GUI** — controls, chat, runtime status, settings, and update checking
- **Local Voice** — Whisper/faster-whisper speech input and Kokoro speech output
- **AI Visualizer** — animated JARVIS faces and thinking state
- **Barehands** — webcam-based hand-tracking interface
- **Memory Vault** — persistent Markdown-based memory
- **Research Tools** — project files, archives, local tools, and optional web research
- **Diagnostics** — rotating logs and crash/error logging
- **Desktop Launcher** — Linux desktop and application-menu launcher support
- **Updater** — checks the configured Releases branch for available packages

## Quick Start

### Launch the GUI

```bash
./start_gui.sh
```

Or run it directly:

```bash
./venv/bin/python scripts/jarvis_gui.py
```

### Run JARVIS Without the GUI

```bash
./scripts/start_jarvis.sh
```

The launcher prepares the virtual environment, installs the selected requirements, checks local services, and starts the configured runtime.

## Main Components

```text
config/
├── jarvis.json          Runtime configuration
├── system_prompt.md     JARVIS system instructions
└── VERSION              Application version source

scripts/
├── jarvis.py            Main agent runtime
├── jarvis_gui.py        GTK3 desktop application
├── research_tools.py    Research and file tools
├── memory.py            Memory Vault support
└── start_jarvis.sh      Runtime launcher

ai-visualizer/            JARVIS visual interface
barehands/                Hand-tracking interface
Memory_Vault/             Persistent memory
Updates/                  Release/update metadata
```

## Runtime

JARVIS is designed to run locally. Ollama, voice processing, visualizer state, Barehands state, memory, and the main agent runtime remain on the local machine.

Internet access is optional and can be controlled through the application configuration. Research tools include local file/archive inspection and optional web research.

## GUI

The GTK3 application provides controls for:

- Voice
- Visuals
- Barehands
- Internet research
- Diagnostics
- GUI theme
- Desktop launcher creation
- Starting and stopping the configured agent
- Configuring the Agent Name used throughout the GUI and runtime
- Checking for updates

Optional Face and Barehands panels can be embedded through WebKitGTK when available, with browser fallback support where needed.

## Configuration

Primary runtime settings live in:

```text
config/jarvis.json
```

System behavior and agent instructions are maintained in:

```text
config/system_prompt.md
```

The application version is stored in:

```text
config/VERSION
```

The Agent Name is stored in `config/jarvis.json` and defaults to `JARVIS`. Changing it from the GUI updates the visible application branding and the live agent identity.

## Logging

JARVIS keeps diagnostics in rotating log files. Diagnostic output can be enabled for terminal visibility while continuing to log in the background.

The Memory Vault records daily interaction activity and is instructed to save concise continuity checkpoints during meaningful project work so durable decisions, discoveries, blockers, and next steps can survive across sessions.

Logs are intended to make runtime, research, service, and failure investigation easier without requiring diagnostic mode to remain enabled.

## Updates

The GUI checks:

```text
Updates/version.json
```

The update metadata supplies the available package name and the changelog displayed by the update dialog.

## Credits

The AI Visualizer component is based on the work of Jared Rhodenizer (`@jaredrhod`).

## License

GNU General Public License v3.0 (GPL-3.0).

**2019-Present — A-Team Digital Solutions**

See [LICENSE](LICENSE).
