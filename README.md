# A-Team - JARVIS AI - 100% Free & 100% Local

A local-first AI assistant stack built around Ollama + Qwen, with local
speech input/output, selectable visual faces, an optional Hands addon,
persistent memory, and project tools.

## Current Reference Configuration

-   Brain: Ollama / `qwen3.6:27b`
-   Speech input: Whisper `tiny.en`
-   Whisper device: CPU
-   Whisper compute type: `int8`
-   Speech output: Kokoro
-   Speech speed: `1.10`
-   Persistent memory: `Memory_Vault`
-   Workspace: `Project_Folder`
-   Tools: `Project_Folder/Tools`

## Architecture

``` text
User
  |
  v
JARVIS local interface
  |
  +--> Ollama / Qwen --------> Project tools
  |                              |
  |                              v
  |                         Project_Folder
  |
  +--> Whisper ------------> Speech transcription
  |
  +--> Kokoro -------------> Speech output
  |
  +--> AI Visualizer ------> Selectable face
  |
  +--> Barehands ----------> Optional hand interface
  |
  +--> Memory Vault -------> Persistent external memory
```

Qwen is the primary intelligence and decision-maker. JARVIS is the local
voice/text interface and runtime around the model, not a second agent.

## Core Behavior

The project is designed around a simple agent workflow:

1.  Understand the requested end state.
2.  Inspect the relevant environment and tools.
3.  Determine the necessary procedure.
4.  Perform the operation.
5.  Verify the resulting state.
6.  Report the actual result concisely.

The agent should not claim success without evidence.

## Workspace

The default working boundary is:

``` text
Project_Folder
```

Project tools live inside:

``` text
Project_Folder/Tools
```

JARVIS should inspect the workspace instead of requiring the user to
provide every exact filename or command when the environment contains
enough information to discover them.

## File Safety

Copy means copy.

If JARVIS copies:

``` text
Firmware/super.img
```

to a tool input directory, the original must remain in `Firmware/`.

JARVIS must not silently move or delete the source because a processed
copy exists.

Likewise, deleting the contents of a directory does not automatically
authorize deleting the directory itself. Reusable tool directories
should remain unless the user explicitly asks for the directory to be
removed.

After file operations, JARVIS should verify the expected files and
directory structure.

## Persistent Memory

A persistent local Memory Vault is available at:

``` text
Memory_Vault
```

Memory is intended for durable information such as:

-   Important project decisions
-   Long-term preferences
-   Project rules
-   Ongoing project facts
-   Useful technical knowledge
-   Relevant previous project knowledge

It should not permanently store every conversational statement.

A core rule is:

> Never claim to remember something unless it is present in the Memory
> Vault or the current conversation.

When the user establishes a durable project rule or preference, the
memory system can preserve it.

## Configuration

The main configuration file is:

``` text
config/jarvis.json
```

Important configuration sections include:

``` text
model
voice
visuals
hands
memory
```

Example voice configuration:

``` json
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
```

Example visual configuration:

``` json
"visuals": {
  "face": "rain"
}
```

## Face System

The current face choices are:

``` text
board
neural
radial
rain
```

The configured face is stored in:

``` json
"face": "board"
```

Use:

``` bash
./select_face.sh
```

to choose a face.

The selector reads the current face, presents the available choices, and
patches the existing `jarvis.json` value without creating another
configuration source.

The visualizer URL follows the selected face:

``` text
http://127.0.0.1:8790/faces/<face>/
```

For example:

``` text
http://127.0.0.1:8790/faces/rain/
```

## Voice System

Kokoro provides local speech output.

The included voice selector presents friendly names and hides the raw
Kokoro prefixes from the visible menu.

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

Use:

``` bash
./select_jarvis_voice.sh
```

The selector supports:

``` text
1) Single Voice
2) Dual Mixed Voice
```

A single voice is stored normally:

``` json
"kokoro_voice": "af_heart"
```

A dual/mixed selection is stored as two Kokoro IDs separated by a comma:

``` json
"kokoro_voice": "bm_daniel,bm_george"
```

The selector patches the existing `kokoro_voice` value in `jarvis.json`.

## Speech Input

Whisper provides local speech recognition.

Current reference settings:

``` text
Model: tiny.en
Device: CPU
Compute type: int8
```

F4 is the push-to-talk control:

``` text
Hold F4 To Talk
Release F4 To Send
```

Typed input remains available.

## Hands Addon

Barehands is an optional visual addon.

When enabled, the local stage is:

``` text
http://127.0.0.1:8794/stage.html
```

The feature is optional so server/headless installations can omit it.

A minimal installation can retain the core agent, voice, memory, and
project tools without requiring the Hands visual interface.

## Startup

The normal launcher is:

``` bash
./start_jarvis.sh
```

The project also has a wake/start entry point depending on the
installation.

A normal runtime status display reports the actual active configuration,
for example:

``` text
=== JARVIS — LOCAL MODE ===
Brain : Ollama / qwen3.6:27b
Ears  : Whisper / tiny.en
Mouth : Kokoro / bf_emma
Face Name  : Rain
Hands Addon : Enabled
Face Link  : http://127.0.0.1:8790/faces/rain/
Hands Link : http://127.0.0.1:8794/stage.html
```

The runtime status should come from the actual configuration/environment
rather than requiring Qwen to rediscover it with tools.

## Setup

The setup process is intended to support selectable features rather than
forcing every component onto every machine.

Typical setup:

``` bash
./setup.sh
```

This is particularly useful for a server installation that does not need
the visual Hands component.

After setup, the Python environment can be activated with:

``` bash
source venv/bin/activate
```

## Terminal Interface

The terminal supports both keyboard and F4 voice interaction.

Typical interaction:

``` text
⌨️  You:
🗣️  You: ...
🤖 JARVIS: ...
```

The terminal output layer should:

-   Keep the cursor at column zero between turns.
-   Prevent ANSI escape sequences from leaking into visible output.
-   Avoid progressively increasing indentation.
-   Keep tool execution details concise.
-   Show useful results instead of raw terminal noise.

The model's response formatting and the terminal's cursor handling are
separate concerns. The display layer should normalize noisy
Markdown/tool output rather than dumping internal execution details
directly into the conversation.

## Tool Use

Tools are internal evidence and execution mechanisms.

JARVIS should not expose raw tool calls in normal responses.

When tools are required, the intended pattern is:

``` text
Inspect
  ->
Act
  ->
Verify
  ->
Summarize
```

If an operation fails, JARVIS should report the real failure and attempt
reasonable recovery when appropriate.

External content is data, not automatically an instruction. Commands or
instructions discovered in downloaded files, web pages, repositories, or
other external content should be inspected before consequential
execution.

## Output Style

JARVIS is intended to be direct, conversational, and concise.

Routine answers should avoid:

-   Unnecessary Markdown
-   Large decorative headings
-   Markdown tables
-   Raw tool output
-   Internal planning
-   Verbose directory listings
-   Repeating information the user did not ask for

The useful result should come first.

For speech output, responses should sound natural when spoken. Markdown
punctuation, URLs, hashes, file paths, and terminal symbols should not
be read aloud unless relevant.

## Testing

After setup or configuration changes, test the following.

### Runtime Identity

Ask:

``` text
What model are you running?
```

The response should match the active runtime configuration.

### Workspace

Ask JARVIS to find a known project file and verify that the returned
path actually exists.

### Copy Safety

Ask JARVIS to copy a file and verify both:

``` text
destination exists
source still exists
```

### Tool Operation

Ask JARVIS to perform a real project operation using an installed tool.
It should inspect the tool, execute the operation, verify the result,
and summarize the outcome.

### Memory

Ask JARVIS to remember a durable project rule, then ask what it
remembers. The result should correspond to actual Memory Vault content.

### Face

Run:

``` bash
./select_face.sh
```

Change the face and restart JARVIS. Confirm the displayed face name and
link.

### Voice

Run:

``` bash
./select_jarvis_voice.sh
```

Choose a single or dual voice, restart JARVIS, and confirm the displayed
Kokoro configuration.

### F4

Hold and release F4 repeatedly. There should be no visible
escape-sequence leakage, stuck recording state, or progressive terminal
indentation.

## Troubleshooting

### Ollama Python Module

If Python reports:

``` text
ModuleNotFoundError: No module named 'ollama'
```

activate the project virtual environment and install the project's
dependencies:

``` bash
source venv/bin/activate
```

### Model Request Errors

An error such as:

``` text
no user query found in messages
```

indicates a problem in the message construction/tool-result pipeline
before the request reaches the local model. Check the message
construction and tool-result handling rather than the voice or
visualizer.

### Face Name Shows a Python Method

Incorrect:

``` python
face_name.capitalize
```

Correct:

``` python
face_name.capitalize()
```

The desired output is:

``` text
Face Name  : Rain
```

### Hands URL Prints Literally

Incorrect:

``` python
print("Hands Link : {hands_url}")
```

Correct:

``` python
print(f"Hands Link : {hands_url}")
```

The launcher should export:

``` bash
FACE_URL="http://127.0.0.1:8790/faces/$FACE_NAME/"
HANDS_URL="http://127.0.0.1:8794/stage.html"

export FACE_URL
export HANDS_URL
```

The Python runtime can read them with:

``` python
os.environ.get("FACE_URL", "")
os.environ.get("HANDS_URL", "")
```

### JSON Voice Value Contains a Newline

A valid voice setting is:

``` json
"kokoro_voice": "af_jessica",
```

or:

``` json
"kokoro_voice": "bm_daniel,bm_george",
```

The value must remain on one line.

Validate the configuration with:

``` bash
python3 -m json.tool config/jarvis.json >/dev/null
```

### Progressive Terminal Indentation

If each new line appears farther to the right, check the terminal
raw-mode/output handling in `jarvis.py`.

Raw input mode must not permanently disable normal newline output
processing. The terminal should return to column zero after each printed
line.

## Project Layout

A representative installation:

``` text
local-jarvis/
├── config/
│   └── jarvis.json
├── ai-visualizer/
├── barehands/
├── Project_Folder/
│   └── Tools/
├── Memory_Vault/
├── venv/
├── jarvis.py
├── start_jarvis.sh
├── wake_jarvis.sh
├── setup.sh
├── select_face.sh
├── select_jarvis_voice.sh
└── README.md
```

The exact layout can evolve.

## Project Philosophy

JARVIS Local is designed around:

### Local First

The primary AI path is local:

``` text
User
 ->
JARVIS
 ->
Ollama / Qwen
 ->
Local tools and workspace
```

### Agent First

When the environment provides the ability to perform a task, JARVIS
should perform it instead of merely describing how the user could do it.

### Inspect Before Acting

Relevant files, scripts, documentation, and tool usage should be
inspected before modification when useful.

### Verify Before Claiming Success

Starting a command is not the same as completing a task. The requested
end state must be verified.

### Preserve User Data

Copying preserves the original source. Cleanup should remove temporary
data without destroying reusable directories unless explicitly
requested.

### Simple Configuration

Small selectors handle routine face and voice choices without requiring
manual JSON editing.

### Optional Components

Visual features should remain optional so the same project can be used
on a full desktop system or a server.

### Concise Interface

The terminal should show useful results without exposing internal tool
plumbing.

## Future Development

Potential areas include:

-   Additional face themes and animations
-   More Kokoro voice options
-   More optional setup components
-   Additional project tools
-   Improved tool-result summarization
-   Expanded memory organization
-   More robust model selection
-   Improved headless/server operation
-   Further terminal UI improvements
-   Additional verification and recovery logic

## License

Add the project's chosen license before publishing.

Before publishing the repository, review the licensing and
redistribution requirements of bundled dependencies, models, binaries,
scripts, and visual assets.

## Quick Start

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

## Final

The goal of JARVIS Local is not to surround a model with unnecessary
layers.

It is a practical local agent built from:

``` text
Local AI
+
Real Tools
+
Persistent Memory
+
Voice
+
Optional Visuals
=
A Useful Local Agent
```
