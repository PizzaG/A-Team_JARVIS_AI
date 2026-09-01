# JARVIS Local

JARVIS Local is a local-first AI assistant and agent runtime built
around **Ollama + Qwen**. It combines a local language model with real
project tools, persistent Markdown-based memory, optional local voice
input/output, an optional animated face, and an optional Barehands
visual interface.

The project is designed to be useful on a desktop while also supporting
a reduced feature set for server or headless installations.

> **Current source baseline**
>
> -   Model: `qwen3.6:27b`
> -   Backend: Ollama
> -   Speech input: Faster-Whisper `tiny.en`
> -   Speech input device: CPU
> -   Whisper compute type: `int8`
> -   Speech output: Kokoro
> -   Current configured Kokoro voice: `bf_emma`
> -   Speech speed: `1.10`
> -   Push-to-talk: F4
> -   Current face: `rain`
> -   Barehands: enabled
> -   Internet tools: enabled
> -   Persistent Memory Vault: enabled
> -   Project workspace: `Project_Folder`
> -   Project tools: `Project_Folder/Tools`

------------------------------------------------------------------------

## Table of Contents

-   [Overview](#overview)
-   [Architecture](#architecture)
-   [Project Structure](#project-structure)
-   [Requirements](#requirements)
-   [Installation](#installation)
-   [Interactive Setup](#interactive-setup)
-   [Configuration](#configuration)
-   [Starting JARVIS](#starting-jarvis)
-   [Runtime Status](#runtime-status)
-   [Voice System](#voice-system)
-   [Face System](#face-system)
-   [Barehands](#barehands)
-   [Persistent Memory](#persistent-memory)
-   [Project Tools](#project-tools)
-   [Internet Research](#internet-research)
-   [Agent Behavior](#agent-behavior)
-   [File Safety](#file-safety)
-   [Terminal Interface](#terminal-interface)
-   [Selectors](#selectors)
-   [Testing](#testing)
-   [Troubleshooting](#troubleshooting)
-   [Customization](#customization)
-   [Server / Reduced Installations](#server--reduced-installations)
-   [Security Considerations](#security-considerations)
-   [Development Notes](#development-notes)
-   [Future Development](#future-development)
-   [License](#license)

------------------------------------------------------------------------

# Overview

JARVIS is the local interface and runtime around the language model.
**Qwen is the primary intelligence and decision-maker.**

The design deliberately avoids treating JARVIS and Qwen as two separate
agents.

The basic flow is:

``` text
User
 |
 +--> Keyboard
 |
 +--> F4 + Microphone
 |
 v
JARVIS Runtime
 |
 +--> Ollama / Qwen
 |       |
 |       +--> Project Tools
 |       +--> Memory
 |       +--> Internet Research
 |
 +--> Whisper
 |
 +--> Kokoro
 |
 +--> AI Visualizer
 |
 +--> Barehands
 |
 v
Project_Folder / Memory_Vault
```

The result is a local assistant that can answer questions, inspect a
project, operate project tools, remember durable information, research
the web when enabled, and speak responses locally.

------------------------------------------------------------------------

# Architecture

## Brain

The language model is served locally through Ollama.

Current model:

``` text
qwen3.6:27b
```

The model is configured in:

``` text
config/jarvis.json
```

The runtime uses the Ollama Python client and preserves the model's
native assistant/tool-call message structure during multi-step tool
execution.

This is important for Qwen's tool-calling workflow.

## Voice Input

Voice input uses:

``` text
Faster-Whisper
```

Current model:

``` text
tiny.en
```

Current settings:

``` text
Device: CPU
Compute type: int8
```

Push-to-talk is controlled through F4.

``` text
Hold F4 To Talk
Release F4 To Send
```

Typed input is also supported.

## Voice Output

Kokoro provides local speech synthesis.

Current reference settings:

``` text
Sample rate: 24000
Speed: 1.10
Speech normalization: enabled
```

The voice is configurable through the voice selector.

## Visuals

The AI Visualizer is an optional local web interface.

The configured face is stored in:

``` text
config/jarvis.json
```

Current face:

``` text
rain
```

The visualizer uses:

``` text
http://127.0.0.1:8790/
```

with the selected face exposed at:

``` text
http://127.0.0.1:8790/faces/<face>/
```

## Hands

Barehands is an optional visual addon.

Current stage:

``` text
http://127.0.0.1:8794/stage.html
```

The feature can be disabled for installations that do not need it.

------------------------------------------------------------------------

# Project Structure

The current source contains the following major components:

``` text
local-jarvis/
├── ai-visualizer/
├── barehands/
├── config/
│   ├── jarvis.json
│   └── system_prompt.md
├── Memory_Vault/
├── Project_Folder/
│   └── Tools/
├── jarvis.py
├── agent_tools.py
├── research_tools.py
├── memory.py
├── local_voice.py
├── start_jarvis.sh
├── wake_jarvis.sh
├── setup_jarvis.sh
├── select_jarvis_face.sh
├── select_jarvis_voice.sh
├── requirements-core.txt
├── requirements-voice.txt
├── requirements-web.txt
├── LOCAL_INSTALL.md
├── LOCAL_JARVIS.md
├── MEMORY.md
├── RESEARCH.md
├── VOICE_SELECTOR.md
└── VERSION
```

The exact project contents may expand as development continues.

------------------------------------------------------------------------

# Requirements

The project is designed for Linux.

The setup process currently expects:

-   Python 3
-   `curl`
-   A supported Linux package manager such as `apt-get` or `pacman` for
    automatic system dependency installation
-   Ollama
-   A working Python virtual environment

Voice installations additionally require native components such as:

-   PortAudio
-   libsndfile
-   espeak-ng
-   Python development/build support

The setup script installs these when needed on supported Linux
distributions.

------------------------------------------------------------------------

# Installation

The primary setup script is:

``` bash
./setup_jarvis.sh
```

The setup script:

1.  Checks for Python and curl.
2.  Presents feature choices.
3.  Creates or reuses the Python virtual environment.
4.  Installs core dependencies.
5.  Installs optional voice dependencies when selected.
6.  Installs web dependencies when Internet tools are selected.
7.  Configures the selected model.
8.  Configures visual features.
9.  Configures the selected face.
10. Configures Memory Vault.
11. Configures Internet tools.
12. Checks Ollama.
13. Offers to start Ollama when it is not reachable.
14. Offers to pull the selected model when it is not installed.
15. Writes the selected feature configuration to `config/jarvis.json`.

The setup process is designed to be rerunnable.

------------------------------------------------------------------------

# Interactive Setup

One of the project's goals is to avoid installing features that a
particular machine does not need.

When setup runs, it asks about:

``` text
Voice input/output
AI Visualizer
Barehands
Persistent Memory Vault
Internet/web tools
Ollama model
Face
```

The defaults currently favor enabling the features.

## Feature Selection

The setup logic currently starts with:

``` text
Voice     = optional
Visualizer = optional
Barehands = optional
Memory    = enabled by default
Internet  = enabled by default
```

Barehands is only offered when the AI Visualizer is enabled.

This allows a server installation to omit the visual components.

## Model Selection

The setup default is:

``` text
qwen3.6:27b
```

The user can enter a different Ollama model during setup.

If Ollama is available and the selected model is missing, setup offers
to pull it.

------------------------------------------------------------------------

# Configuration

The main configuration file is:

``` text
config/jarvis.json
```

The current configuration structure includes:

``` json
{
  "name": "JARVIS",
  "ollama": {
    "url": "http://127.0.0.1:11434/api/chat",
    "model": "qwen3.6:27b",
    "temperature": 0.7,
    "max_tokens": 4096,
    "timeout": 300,
    "max_tool_rounds": 20,
    "think": true,
    "num_ctx": 32768
  },
  "voice": {
    "whisper_model": "tiny.en",
    "whisper_device": "cpu",
    "whisper_compute_type": "int8",
    "kokoro_voice": "bf_emma",
    "sample_rate": 24000,
    "speed": 1.10,
    "speech_normalization": true,
    "enabled": true
  }
}
```

Other configuration sections include:

``` text
push_to_talk
visuals
research
memory
display
```

## Display Configuration

The current configuration uses:

``` json
"display": {
  "show_tool_activity": false
}
```

This is intentional.

Tool execution remains available internally, but raw tool activity is
not normally dumped into the user's terminal.

------------------------------------------------------------------------

# System Prompt

The primary behavioral prompt is:

``` text
config/system_prompt.md
```

If this file exists, JARVIS loads it as the base system prompt.

The runtime then appends authoritative runtime context containing
information such as:

``` text
AI model
AI backend
Speech recognition
Speech synthesis
Project workspace
Project tools directory
Persistent memory vault
Internet tools
Memory boot context
```

This allows JARVIS to answer runtime-identity questions directly instead
of using tools to rediscover information that the runtime already knows.

The configuration also contains a fallback `system_prompt` value for
cases where the external prompt file is unavailable.

------------------------------------------------------------------------

# Starting JARVIS

The primary launcher is:

``` bash
./start_jarvis.sh
```

The project also provides:

``` bash
./wake_jarvis.sh
```

depending on the desired startup entry point.

The startup process:

1.  Enters the project's Python virtual environment.
2.  Synchronizes core dependencies.
3.  Installs optional voice dependencies when voice is enabled.
4.  Installs web dependencies when Internet tools are enabled.
5.  Ensures local state directories exist.
6.  Checks Ollama.
7.  Starts Ollama only when needed.
8.  Starts the AI Visualizer when enabled.
9.  Starts Barehands when enabled.
10. Exports the face and Hands URLs.
11. Starts `jarvis.py`.

The launcher deliberately does not use a generic `pkill` against
unrelated `server.py` processes.

It also does not kill an Ollama service that it did not start.

------------------------------------------------------------------------

# Runtime Status

JARVIS displays its active runtime configuration when starting.

A current example is:

``` text
=== JARVIS — LOCAL MODE ===
Brain : Ollama / qwen3.6:27b
Ears  : Whisper / tiny.en
Mouth : Kokoro / bf_emma
Face Name  : Rain
Hands Addon : Enabled
Face Link  : http://127.0.0.1:8790/faces/rain/
Hands Link : http://127.0.0.1:8794/stage.html
Loading Persistent Memory ...
✓ Local Memory Vault Ready
Loading Kokoro Voice Engine ...
✓ Local Kokoro Ready
Project Root  : /home/.../Project_Folder
Memory Vault  : /home/.../Memory_Vault
```

The runtime reads the face URL and Hands URL from the environment
exported by the launcher.

The face name is displayed using normal capitalization:

``` text
rain -> Rain
neural -> Neural
radial -> Radial
board -> Board
```

------------------------------------------------------------------------

# Voice System

Voice functionality consists of two independent local components:

``` text
Whisper -> speech recognition
Kokoro  -> speech synthesis
```

## Whisper

Configured through:

``` json
"whisper_model": "tiny.en",
"whisper_device": "cpu",
"whisper_compute_type": "int8"
```

## Kokoro

Configured through:

``` json
"kokoro_voice": "bf_emma",
"sample_rate": 24000,
"speed": 1.10,
"speech_normalization": true
```

## Voice Selection

Run:

``` bash
./select_jarvis_voice.sh
```

The selector supports:

``` text
1) Single Voice
2) Dual Mixed Voice
```

The visible menu uses friendly names and hides the raw Kokoro prefixes.

### American Female

``` text
heart
alloy
aoede
bella
jessica
kore
nicole
nova
river
sarah
sky
```

### American Male

``` text
adam
echo
eric
fenrir
liam
michael
onyx
puck
santa
```

### British Female

``` text
alice
emma
isabella
lily
```

### British Male

``` text
daniel
fable
george
lewis
```

The selector maps those names to Kokoro IDs.

Examples:

``` text
heart  -> af_heart
jessica -> af_jessica
emma   -> bf_emma
daniel -> bm_daniel
lewis  -> bm_lewis
```

## Single Voice

A single selection produces:

``` json
"kokoro_voice": "af_heart"
```

## Dual Mixed Voice

Two selected voices are stored as comma-separated Kokoro IDs:

``` json
"kokoro_voice": "bm_daniel,bm_george"
```

The selector modifies the existing `kokoro_voice` setting rather than
creating another configuration file.

## Speech Speed

Current setting:

``` json
"speed": 1.10
```

This is the current preferred project setting.

------------------------------------------------------------------------

# Face System

The current face choices in the project are:

``` text
board
neural
radial
rain
```

The selected face is stored under:

``` json
"visuals": {
  "face": "rain"
}
```

Use:

``` bash
./select_jarvis_face.sh
```

to change it.

The selector:

1.  Reads the existing configuration.
2.  Displays available faces.
3.  Identifies the current face.
4.  Lets the user choose another face.
5.  Patches the existing configuration value.

The launcher then derives:

``` text
FACE_URL=http://127.0.0.1:8790/faces/<face>/
```

and exports it to the JARVIS process.

------------------------------------------------------------------------

# Barehands

Barehands is an optional visual interface.

When enabled:

``` text
http://127.0.0.1:8794/stage.html
```

is available.

The runtime state is communicated through:

``` text
barehands/state/state
```

JARVIS can publish states such as:

``` text
idle
listening
thinking
speaking
```

The waveform/state files are treated as transient runtime data and are
cleared during startup/shutdown as appropriate.

------------------------------------------------------------------------

# Persistent Memory

The Memory Vault is a local, Markdown-first persistent memory system.

The configured root is:

``` text
Memory_Vault
```

The vault currently organizes information into:

``` text
Memory_Vault/
├── 01 - Daily Notes/
├── 02 - Profile/
├── 03 - Projects/
├── 04 - Knowledge/
├── 05 - Jobs/
├── VAULT-INDEX.md
└── Active Priorities.md
```

## Memory Boot Context

At startup, JARVIS loads relevant foundational memory including:

-   Vault index
-   Active priorities
-   Profile
-   Current daily note

The loaded memory is inserted into the runtime context given to Qwen.

## Memory Search

The memory system searches Markdown files and scores matches based on
query terms.

## Remembering

The `remember` tool writes durable information into the vault and also
records the event in the current daily note.

## Daily Interaction Logging

Interactions are recorded in a compact form rather than dumping
unlimited transcripts into persistent memory.

The user input and assistant response are normalized and truncated
before being written to the daily note.

## Memory Rules

The intended memory behavior is:

-   Remember explicit user requests.
-   Remember durable project rules and decisions.
-   Remember useful long-term preferences.
-   Search memory when previous project knowledge is materially
    relevant.
-   Do not save every conversational statement.
-   Do not invent memories.
-   Prefer useful durable information over conversational noise.
-   Avoid unnecessary duplicate memories.

------------------------------------------------------------------------

# Project Tools

JARVIS tools operate inside the configured project workspace.

The default workspace is:

``` text
Project_Folder
```

Project tools live at:

``` text
Project_Folder/Tools
```

The tool layer includes operations for:

``` text
List project files
Read project files
Search project files
Inspect files
List archives
Extract archives
Find project tools
Run project commands
Copy files/directories
Move files/directories
Delete files/directories
Search the web
Open web pages
Download web files
Remember information
Search persistent memory
```

## Project Tool Discovery

JARVIS can search `Project_Folder/Tools` for scripts and binaries and
inspect readable source when determining how a tool works.

This allows the agent to discover project-specific utilities instead of
requiring every tool to be hard-coded into the assistant.

## Project Commands

Project commands execute with their working directory constrained to the
project sandbox.

Command input is explicitly set to:

``` text
/dev/null
```

This is important because interactive project scripts that wait for
`read`, `pause`, or similar input must not steal JARVIS's own terminal
input.

Project command output is normally kept internal for Qwen's reasoning.

The `show_output` option exists for cases where raw command output is
explicitly useful.

------------------------------------------------------------------------

# Internet Research

Internet tools are optional.

When enabled, JARVIS provides:

``` text
web_search
open_web_page
download_web_file
```

The web search backend uses the local DDGS Python package.

Web searches run in a separate process with a real timeout so a stalled
network/search provider does not freeze the main voice loop.

Current web search timeout:

``` text
15 seconds
```

The underlying DDGS request uses a shorter HTTP timeout.

Downloads are restricted to the project `downloads` directory and have a
maximum size of:

``` text
512 MiB
```

Only HTTP and HTTPS URLs are accepted by the URL tools.

------------------------------------------------------------------------

# Agent Behavior

The behavioral rules live in:

``` text
config/system_prompt.md
```

The current design establishes several important principles.

## Evidence First

Actual files, command results, tool results, and authoritative research
are treated as evidence.

JARVIS should not guess when the environment can be inspected.

## Inspect Before Modifying

When useful, JARVIS should inspect:

-   README files
-   Scripts
-   Configuration
-   Usage text
-   Tool source
-   Surrounding project files

before modifying or executing a project tool.

## Complete the Task

When the user gives JARVIS a goal, the agent should determine reasonable
intermediate steps itself.

It should not require the user to specify every filename, command,
conversion, or discovery step when the environment provides enough
information.

## Verify Results

Running a command is not automatically equivalent to completing the
user's task.

The requested end state should be checked before claiming success.

## Do Not Invent Results

JARVIS should never invent:

-   Tool output
-   File contents
-   Paths
-   Actions
-   Citations
-   Success
-   Memories

If something failed, the actual failure should be reported.

------------------------------------------------------------------------

# File Safety

File safety is an explicit project rule.

## Copy Means Copy

If the user asks JARVIS to copy a file:

``` text
source -> destination
```

the source remains intact.

The agent must not silently:

-   Move the original
-   Delete the original
-   Treat the source as disposable
-   Assume permission to remove it

For example:

``` text
Firmware/super.img
```

copied to a tool directory must remain in:

``` text
Firmware/super.img
```

unless the user explicitly asks for the original to be moved or deleted.

## Ambiguous Copy vs Move

If the user's wording is ambiguous between copying and moving:

``` text
Preserve the original.
```

JARVIS must not infer permission to delete the source.

## Directory Safety

Deleting a directory is different from deleting the contents of a
directory.

If the user asks to remove temporary files from a reusable tool
directory, the directory itself should remain unless the user explicitly
requests its removal.

## Destructive Operations

The delete tool requires:

``` text
confirm=true
```

The system prompt instructs JARVIS to ask the user for confirmation
before clearly destructive or irreversible operations unless the user
has already clearly requested them.

------------------------------------------------------------------------

# Terminal Interface

The terminal supports both typed and voice interaction.

Typical interaction:

``` text
⌨️  You:
🗣️  You: What model are you running?
🤖 JARVIS: I'm running Qwen 3.6 with 27 billion parameters through Ollama.

⌨️  You:
```

## Tool Output

Raw tool activity is disabled by default:

``` json
"show_tool_activity": false
```

This means the terminal should not normally display lines such as:

``` text
🔧 Qwen -> list_project_files
```

unless explicitly enabled.

Tool output remains available internally to the agent.

## Display Formatting

The display layer contains a `format_for_display()` function that
converts Qwen's Markdown-friendly responses into cleaner plain-terminal
output.

It currently handles:

-   Markdown headings
-   Bold markers
-   Underscore emphasis
-   Backticks
-   Markdown links
-   Markdown table rows
-   Excess whitespace

The purpose is to make terminal output readable without requiring Qwen
to avoid all useful formatting internally.

## F4 Terminal Handling

Linux terminal raw mode is required for reliable F4 push-to-talk
handling.

The runtime also restores normal output newline processing after
entering raw mode.

This prevents the classic progressive indentation problem where every
new response begins farther to the right than the previous one.

F4 escape sequences are consumed rather than displayed as raw terminal
characters.

------------------------------------------------------------------------

# Selectors

The project intentionally uses small Bash selectors for common
configuration choices.

## Face Selector

``` bash
./select_jarvis_face.sh
```

Changes:

``` text
visuals.face
```

## Voice Selector

``` bash
./select_jarvis_voice.sh
```

Changes:

``` text
voice.kokoro_voice
```

The selectors operate on the existing configuration rather than creating
competing configuration files.

------------------------------------------------------------------------

# Testing

After setup, test the system in layers.

## 1. Startup

Run:

``` bash
./start_jarvis.sh
```

Confirm that the runtime banner reports the expected:

``` text
Model
Whisper
Kokoro
Face
Hands
Project Root
Memory Vault
```

## 2. Model

Ask:

``` text
What model are you running?
```

The response should correspond to the configured runtime model.

## 3. Memory

Ask JARVIS to remember a durable project rule.

Then ask what it remembers.

The result should come from actual Memory Vault data.

## 4. Workspace

Ask JARVIS to locate a known project file.

Verify that the returned file actually exists.

## 5. Copy Safety

Ask JARVIS to copy a known file.

Verify:

``` text
Destination exists.
Original still exists.
```

## 6. Tool Execution

Ask JARVIS to use a known project tool.

It should:

``` text
Inspect
 -> Execute
 -> Verify
 -> Summarize
```

## 7. Voice

Change the Kokoro voice:

``` bash
./select_jarvis_voice.sh
```

Restart JARVIS and verify the runtime banner reports the new voice.

## 8. Dual Voice

Select two voices and verify the configuration contains:

``` json
"kokoro_voice": "bm_daniel,bm_george"
```

## 9. Face

Run:

``` bash
./select_jarvis_face.sh
```

Select a different face.

Restart and verify:

``` text
Face Name  : Rain
Face Link  : http://127.0.0.1:8790/faces/rain/
```

## 10. F4

Hold and release F4 repeatedly.

There should be:

-   No raw escape-sequence leakage
-   No progressive indentation
-   No stuck recording state
-   No terminal input corruption

## 11. Web Research

Ask a current-information question when Internet tools are enabled.

Confirm that JARVIS uses the web tool rather than pretending to have
current information from memory.

------------------------------------------------------------------------

# Troubleshooting

## `ModuleNotFoundError: No module named 'ollama'`

Activate the project virtual environment:

``` bash
source venv/bin/activate
```

Then rerun the setup or install the core requirements:

``` bash
python -m pip install -r requirements-core.txt
```

## `no user query found in messages`

This is an Ollama/Qwen message-construction or tool-call pipeline
problem.

The current runtime preserves Ollama's actual assistant message object
when handling tool calls because reconstructing those messages manually
caused broken multi-step conversation state with Qwen.

If this error returns, inspect the message history/tool-call handling
rather than changing the voice or visual components.

## Face Name Displays a Python Method

Incorrect:

``` python
face_name.capitalize
```

Correct:

``` python
face_name.capitalize()
```

Expected:

``` text
Face Name  : Rain
```

## Hands URL Displays Literally

Incorrect:

``` python
print("Hands Link : {hands_url}")
```

Correct:

``` python
print(f"Hands Link : {hands_url}")
```

The launcher exports:

``` bash
FACE_URL="http://127.0.0.1:8790/faces/$FACE_NAME/"
HANDS_URL="http://127.0.0.1:8794/stage.html"

export FACE_URL
export HANDS_URL
```

## Progressive Terminal Indentation

If each successive line starts farther to the right, check the terminal
raw-mode/output handling in `jarvis.py`.

Raw input mode must not leave output newline processing disabled.

The runtime should preserve normal newline conversion so each `\n`
returns output to column zero.

## Raw F4 Escape Sequences Appear

The terminal input loop must consume the terminal-generated F4 escape
sequence while recording.

Do not remove raw-mode handling simply to hide the characters; doing so
can break the F4 workflow.

## Voice Selector Corrupts JSON

A valid single voice looks like:

``` json
"kokoro_voice": "af_jessica",
```

A valid dual voice looks like:

``` json
"kokoro_voice": "bm_daniel,bm_george",
```

The entire value should remain on one line.

Validate the JSON with:

``` bash
python3 -m json.tool config/jarvis.json >/dev/null
```

## Project Tool Appears to Hang

Project commands are intentionally launched with:

``` text
stdin = /dev/null
```

This prevents a project script from consuming JARVIS's own terminal
input.

Scripts that require interactive input are therefore not suitable for
direct execution through the project command tool unless they provide a
non-interactive mode.

## Web Search Hangs

Web search runs in a separate worker process with a hard timeout.

If the provider is slow or unavailable, JARVIS should report the
web-search failure while keeping the main agent running.

------------------------------------------------------------------------

# Customization

## Change the Model

Edit:

``` text
config/jarvis.json
```

or rerun:

``` bash
./setup_jarvis.sh
```

and enter the desired Ollama model.

Make sure the model exists locally:

``` bash
ollama list
```

## Change the Face

Use:

``` bash
./select_jarvis_face.sh
```

## Change the Voice

Use:

``` bash
./select_jarvis_voice.sh
```

## Change Speech Speed

Edit:

``` json
"speed": 1.10
```

## Disable Voice

Set:

``` json
"voice": {
  "enabled": false
}
```

The runtime will then operate through typed input.

## Disable Visuals

Set:

``` json
"visuals": {
  "enabled": false
}
```

## Disable Barehands

Set:

``` json
"barehands_enabled": false
```

## Disable Internet Tools

Set:

``` json
"research": {
  "internet": false
}
```

## Disable Memory

Set:

``` json
"memory": {
  "enabled": false
}
```

------------------------------------------------------------------------

# Server / Reduced Installations

A major design goal is that JARVIS does not need every feature on every
machine.

For a server installation, the following can be omitted:

``` text
AI Visualizer
Barehands
Voice input/output
Internet tools
```

depending on the intended use.

For example, a server can be configured around:

``` text
Ollama
Qwen
Project tools
Memory Vault
Typed interface
```

while a desktop installation can enable:

``` text
Voice
AI Visualizer
Barehands
Internet research
```

The interactive setup is intended to make these choices before optional
dependencies are installed.

------------------------------------------------------------------------

# Security Considerations

JARVIS performs real local file operations and can execute project
commands. The project therefore treats the workspace boundary and
external instructions as important safety boundaries.

## Workspace Boundary

Project file tools are constrained to:

``` text
Project_Folder
```

Project commands run inside that sandbox.

## External Content

Web pages, downloaded files, repositories, archives, and other external
content are treated as data.

Instructions found inside external content are not automatically trusted
as user instructions.

Consequential commands discovered in external content should be
inspected before execution.

## Downloads

Web downloads are limited to the project's:

``` text
downloads/
```

directory and have a 512 MiB size limit.

## Secrets

Passwords, API keys, authentication tokens, and private credentials
should not be stored in persistent memory, conversation exports, or
project documentation unless explicitly required for a safe handling
operation.

------------------------------------------------------------------------

# Development Notes

## Runtime and Configuration Separation

`jarvis.py` reads:

``` text
config/jarvis.json
```

and uses:

``` text
config/system_prompt.md
```

as the primary behavioral prompt.

This keeps behavior and runtime configuration separate from the Python
implementation.

## Optional Dependency Groups

Dependencies are divided into:

``` text
requirements-core.txt
requirements-voice.txt
requirements-web.txt
```

Core:

``` text
requests
ollama
```

Voice:

``` text
numpy
scipy
sounddevice
pynput
faster-whisper
kokoro
misaki[en]
soundfile
torch
```

Web:

``` text
ddgs
```

The launcher installs optional groups according to configuration.

## Local Voice Engine

Kokoro is loaded through the local voice implementation and uses:

``` text
hexgrad/Kokoro-82M
```

The project suppresses unnecessary Hugging Face progress/telemetry
output to keep the JARVIS terminal clean.

## State Buses

The visual components communicate through small local state files.

AI Visualizer:

``` text
ai-visualizer/.voice_state
```

Barehands:

``` text
barehands/state/state
```

Transient waveform files are also used and cleared as appropriate.

------------------------------------------------------------------------

# Future Development

Potential future improvements include:

-   More selectable faces
-   Additional face animations
-   More voice options
-   Improved voice mixing controls
-   More optional setup modules
-   Additional project tools
-   Improved tool-result summarization
-   More sophisticated memory consolidation
-   Additional model selection helpers
-   Improved headless operation
-   Better server deployment support
-   Further terminal UI improvements
-   More automated installation validation
-   Additional recovery and verification logic

The current architecture is intentionally modular so these additions can
be made without turning the runtime into a collection of unnecessary
layers.

------------------------------------------------------------------------

# License

Add the project's chosen license before publishing the repository.

Before making the repository public, review the licensing and
redistribution requirements for:

-   Models
-   Python packages
-   Third-party scripts
-   Bundled binaries
-   Visual assets
-   AI Visualizer assets
-   Barehands assets
-   Any included project tools

Do not assume that every component of a local AI stack has the same
license as this project.

------------------------------------------------------------------------

# Quick Start

For an already prepared installation:

``` bash
cd ~/local-jarvis
source venv/bin/activate
./start_jarvis.sh
```

Then:

``` text
Hold F4 To Talk.
Release F4 To Send.
```

Typed input is also available.

For a new installation:

``` bash
cd ~/local-jarvis
./setup_jarvis.sh
```

Choose the features you want, configure the model and face, then start
JARVIS.

------------------------------------------------------------------------

# Design Summary

JARVIS Local is built around a straightforward idea:

``` text
Local AI
+
Real Tools
+
Persistent Memory
+
Local Voice
+
Optional Visuals
=
A Useful Local Agent
```

The model supplies the intelligence.

JARVIS supplies the runtime.

Tools provide real-world project capabilities.

Memory provides persistence.

Voice and visuals make the interface more natural.

Optional components keep the system practical on machines that do not
need the complete desktop experience.
