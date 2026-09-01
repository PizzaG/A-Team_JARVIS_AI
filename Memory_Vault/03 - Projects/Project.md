# A-Team JARVIS — Project Handoff

## Purpose

A-Team JARVIS is a local-first voice and text AI assistant built around a local Qwen model served by Ollama. JARVIS is the interface/runtime shell around the model; Qwen is the primary intelligence, reasoning engine, and decision-maker.

This document is a handoff reference for another local AI. The actual current source files are authoritative if this document ever conflicts with them.

## Core Architecture

```text
USER
 ├── voice → Whisper → text
 └── text input
          ↓
       JARVIS.py
          ↓
     Ollama / Qwen
          ↓
   reasoning + tools
     ┌────┼───────────────┐
     ↓    ↓               ↓
 Project  Internet     Memory_Vault
 Folder   research
     ↓
Project_Folder/Tools

Qwen response
     ↓
   Kokoro
     ↓
 speech output
     ↓
 AI Visualizer / waveform
     ↓
 selected face

Optional:
Barehands
```

Critical design decision: **JARVIS is not a second AI agent. Qwen is the agent.** JARVIS provides the local voice/text interface, runtime integration, tools, memory plumbing, and visual/hardware integrations.

## Current Configuration

`config/jarvis.json` is the primary JARVIS configuration source of truth.

Current relevant configuration:

```json
{
  "name": "JARVIS",
  "ollama": {
    "url": "http://127.0.0.1:11434/api/chat",
    "model": "qwen3.6:27b",
    "temperature": 0.55,
    "max_tokens": 8192,
    "timeout": 300,
    "max_tool_rounds": 15,
    "think": true,
    "num_ctx": 32768
  },
  "voice": {
    "whisper_model": "tiny.en",
    "whisper_device": "cpu",
    "whisper_compute_type": "int8",
    "kokoro_voice": "af_jessica,bf_lily",
    "sample_rate": 24000,
    "speed": 1.10,
    "speech_normalization": true,
    "enabled": true
  },
  "push_to_talk": {
    "key": "f4",
    "sample_rate": 16000
  },
  "visuals": {
    "ai_visualizer_bus": "ai-visualizer",
    "barehands_state": "barehands/state",
    "enabled": true,
    "face": "a-team-moto-pad",
    "barehands_enabled": true
  },
  "research": {
    "Root": "Project_Folder",
    "max_results": 500,
    "internet": true,
    "max_web_results": 10
  },
  "memory": {
    "enabled": true,
    "Root": "Memory_Vault",
    "daily_notes": true,
    "auto_log": true
  },
  "display": {
    "show_tool_activity": true
  }
}
```

## LLM / Ollama

JARVIS currently uses:

```text
Model: qwen3.6:27b
Endpoint: http://127.0.0.1:11434/api/chat
Temperature: 0.55
Max output tokens: 8192
Timeout: 300 seconds
Max tool rounds: 15
Thinking: enabled
Context: 32768 tokens
```

Do not change these simply because another value seems theoretically better. Benchmark first when performance matters.

Aider is separate and currently uses `qwen3.8:27b`; do not silently standardize the two.

## Voice

Voice input:

```text
Microphone
→ Whisper tiny.en
→ CPU
→ int8
→ text
```

Voice output:

```text
Qwen response
→ Kokoro
→ 24 kHz audio
```

Current Kokoro configuration:

```text
af_jessica,bf_lily
```

This is a dual/mixed voice.

Current speech speed:

```text
1.10
```

Speech normalization is enabled.

Push-to-talk:

```text
F4
```

The voice selector writes `voice.kokoro_voice` in `config/jarvis.json`.

## Dependencies

The current dependency system is feature-separated:

```text
requirements-core.txt
requirements-voice.txt
requirements-web.txt
```

Core:

```text
requests>=2.31
ollama>=0.6.0
```

Voice:

```text
numpy>=1.26
scipy>=1.11
sounddevice>=0.4.6
pynput>=1.7.6
faster-whisper>=1.1
kokoro>=0.9.4
misaki[en]>=0.9.4
soundfile>=0.12
torch>=2.0
```

Web:

```text
ddgs>=9.0
```

`requirements-local.txt` was checked and contains no unique dependency. It is simply the combined dependency set of core + voice + web and is obsolete/redundant.

## Startup

Primary launcher:

```text
start_jarvis.sh
```

It is responsible for:

1. Determining the project root.
2. Checking the Python virtual environment.
3. Installing core dependencies.
4. Reading feature flags from `config/jarvis.json`.
5. Installing optional voice/web dependencies.
6. Setting environment variables.
7. Initializing visualizer/Barehands state.
8. Checking for an existing Ollama service.
9. Starting Ollama only if necessary.
10. Starting AI Visualizer if enabled.
11. Starting Barehands if enabled.
12. Launching `jarvis.py`.

Important environment variables include:

```text
HSA_OVERRIDE_GFX_VERSION
OLLAMA_HOST
OLLAMA_API_BASE
PYTHONWARNINGS
FACE_URL
HANDS_URL
```

Ports:

```text
Ollama       11434
AI Visualizer 8790
Barehands     8794
```

The launcher should use the project's venv Python explicitly for Python/pip operations. Do not bypass PEP 668 with `--break-system-packages`.

## Ollama Process Behavior

The launcher checks:

```text
http://127.0.0.1:11434/api/tags
```

If Ollama is already available, it does not start another instance.

If unavailable, it starts:

```text
ollama serve
```

and tracks the PID only when it started that process.

Do not use broad `pkill` behavior that could terminate an externally managed Ollama service.

Runtime logs are intended to live under:

```text
logs/
```

including `ollama.log`.

## Runtime Logs

The project is being organized so runtime/history files live under:

```text
logs/
```

Expected examples:

```text
logs/
├── ollama.log
├── face.log
├── hands.log
├── .aider.chat.history.md
└── .aider.input.history
```

Configuration belongs under `config/`, not `logs/`.

## Persistent Memory

Persistent memory lives in:

```text
Memory_Vault/
```

Configured as:

```json
"memory": {
  "enabled": true,
  "Root": "Memory_Vault",
  "daily_notes": true,
  "auto_log": true
}
```

Do not introduce a competing memory system without an explicit architecture decision.

## Local Workspace and Tools

Default local research/working root:

```text
Project_Folder/
```

Tools:

```text
Project_Folder/Tools/
```

The system prompt explicitly establishes `Project_Folder` as the working boundary.

## System Prompt

Behavior instructions are in:

```text
system_prompt.md
```

Important rules include:

- Qwen is the primary agent.
- JARVIS is the local interface/runtime shell.
- Inspect before modifying.
- Use tools when genuinely needed.
- Verify resulting state after operations.
- Never invent tool output, paths, file contents, or success.
- Treat actual files and command results as evidence.
- Keep `Project_Folder` as the default local workspace.
- Keep `Memory_Vault` as persistent memory.
- Preserve source files when copying.
- Avoid duplicate configuration.

## AI Visualizer

AI Visualizer runs on:

```text
http://127.0.0.1:8790
```

Faces live under:

```text
ai-visualizer/faces/
```

The configured face is currently:

```text
a-team-moto-pad
```

Faces generally consist of:

```text
ai-visualizer/faces/<face-name>/
├── face.json
└── index.html
```

Image-based faces may additionally contain artwork such as `face.png`.

When a user supplies artwork and asks for a face based on it, the supplied artwork should remain the actual face unless the user explicitly asks for replacement/generation. Effects and HUD elements should be layered around or over the supplied artwork without unnecessarily replacing it.

The visualizer uses the shared:

```text
ai-visualizer/core.js
```

for runtime state/waveform integration.

Important visual states:

```text
idle
listening
thinking
speaking
```

## Face Selector

Script:

```text
select_jarvis_face.sh
```

It:

1. Finds `config/jarvis.json`.
2. Finds `ai-visualizer/faces`.
3. Discovers face directories.
4. Shows the current face.
5. Lets the user select a face.
6. Patches only `visuals.face`.

The existing selector is intentionally simple and known to work. Preserve its mechanism unless there is a concrete reason to replace it.

## Voice Selector

Script:

```text
select_jarvis_voice.sh
```

The UI supports:

```text
Single Voice
Dual Mixed Voice
```

The visible list uses friendly voice names without the internal `af_`, `am_`, `bf_`, and `bm_` prefixes.

The JSON retains the actual Kokoro identifiers.

Example:

```json
"kokoro_voice": "af_jessica,bf_lily"
```

Be careful when modifying this script: previous versions suffered from shell/sed quoting errors and malformed JSON. The working implementation writes a normal JSON string and should be preserved.

## Barehands

Barehands is optional.

Port:

```text
8794
```

Stage:

```text
http://127.0.0.1:8794/stage.html
```

State directory:

```text
barehands/state/
```

The launcher initializes:

```text
barehands/state/state
```

and uses state values such as:

```text
idle
thinking
```

Configuration:

```json
"barehands_enabled": true
```

## State Communication

JARVIS communicates runtime state to visual subsystems.

The important conceptual states are:

```text
idle
listening
thinking
speaking
```

Visual faces should use the existing AI Visualizer state/core mechanism rather than inventing a separate protocol.

## Aider

Aider is a development-time tool, not part of JARVIS runtime.

Observed version:

```text
Aider v0.86.2
```

Observed Aider model:

```text
ollama/qwen3.8:27b
```

Historical Aider config:

```yaml
model: ollama/qwen3.8:27b
openai-api-base: http://localhost:11434
watch-files: true
```

The intended organization is to keep Aider configuration under:

```text
config/.aider.conf.yml
```

but the installed Aider version's configuration discovery/explicit config behavior must be verified before moving the file.

Aider history files are separate from Aider configuration.

## Important Model Distinction

Current JARVIS model:

```text
qwen3.6:27b
```

Current Aider model:

```text
qwen3.8:27b
```

These are separate configuration contexts. Do not silently change either one.

## Important Files

High-value source/configuration files:

```text
jarvis.py
start_jarvis.sh
config/jarvis.json
system_prompt.md

select_jarvis_face.sh
select_jarvis_voice.sh

requirements-core.txt
requirements-voice.txt
requirements-web.txt

ai-visualizer/
barehands/
Project_Folder/
Memory_Vault/
logs/
```

## Development Rules

When continuing development:

```text
inspect
→ understand existing implementation
→ make smallest necessary change
→ syntax-check
→ run/test
→ verify
```

Useful checks:

```bash
bash -n start_jarvis.sh
python3 -m py_compile jarvis.py
python3 -m json.tool config/jarvis.json
```

Do not rewrite working components simply to make them look cleaner.

Do not invent missing project behavior when the source can be inspected.

## Current Status

The project currently has:

- Local Qwen intelligence through Ollama.
- Configurable reasoning and context.
- Whisper speech recognition.
- Kokoro speech synthesis.
- Single and dual voice selection.
- F4 push-to-talk.
- Text input fallback.
- Persistent Memory Vault.
- Local Project_Folder research.
- Optional Internet research.
- AI Visualizer.
- Selectable custom faces.
- A-Team branded custom faces.
- Optional Barehands integration.
- Runtime state communication.
- Feature-separated Python dependencies.
- Dedicated runtime log organization.

## Source-of-Truth Priority

When information conflicts, use:

1. Actual current source code.
2. `config/jarvis.json`.
3. `system_prompt.md`.
4. Current requirement files.
5. This `Project.md`.
6. Historical Aider conversations.
7. General assumptions.

Historical documentation can explain why something was built, but current source wins.

## Do Not Lose These Rules

- Inspect source before changing it.
- Do not guess when the source can answer the question.
- Preserve working mechanisms.
- Keep `config/jarvis.json` as the JARVIS configuration source of truth.
- Keep Qwen as the primary agent.
- Treat JARVIS as the local interface/runtime shell.
- Keep `Project_Folder` as the local working/research boundary.
- Keep `Memory_Vault` as persistent memory.
- Keep runtime logs separate from configuration.
- Do not silently change models, voices, faces, ports, or architecture.
- Verify changes after making them.
- Never claim something was checked unless it was actually checked.
- Use supplied face artwork as the actual face when requested.
- Prefer small, testable changes over architectural churn.
