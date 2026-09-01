# Local JARVIS

JARVIS is the local voice/terminal interface around Ollama + Qwen. Qwen is the agent and decides when to use the available tools.

## Architecture

- Whisper: voice input
- Keyboard: second input
- Ollama / Qwen: reasoning, conversation, planning, and tool selection
- `agent_tools.py`: tool bridge exposed to Qwen through Ollama's native tool-calling API
- Kokoro: local speech output
- `Memory_Vault/`: persistent memory
- `Project_Folder/`: local project workspace; `Project_Folder/Tools/` contains project tools
- `ai-visualizer/` and `barehands/`: visual/hands output

JARVIS does not contain a second planner/agent. Qwen is the agent.
