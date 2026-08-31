# JARVIS Persistent Memory

Jarvis uses `Memory_Vault/` as its persistent, markdown-first external memory.

This follows the core architecture of Jared Rhodenizer's AI Memory Vault: the vault is external to the model, memory is loaded on demand, and durable information is stored as readable Markdown rather than hidden inside the model.

Jarvis-specific adaptation:
- `VAULT-INDEX.md` is the memory operating manual.
- `02 - Profile/` stores durable user/work preferences.
- `03 - Projects/` stores durable project knowledge.
- `04 - Knowledge/` stores reusable technical knowledge.
- `05 - Jobs/` stores task-specific priming/procedures.
- `01 - Daily Notes/` records activity across sessions.

Use "remember that ..." to explicitly persist a fact. Jarvis also records concise daily session entries so work can be resumed later.
