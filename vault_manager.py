"""
vault_manager.py - Persistent Memory Vault Manager for Local AI Agent.
Handles initialization, reading, searching, and updating agent memory files
(SOUL.md, IDENTITY.md, MEMORY.md, LESSONS.md, etc.)
"""
import os
import json
from pathlib import Path

DEFAULT_SOUL = """# SOUL: Who You Are
You are JARVIS, a capable, loyal, highly intelligent AI assistant and desktop companion.
You speak directly, warmly, and concisely with understated competence.
You are running locally on your user's machine with direct access to local tools, files, and memory.
"""

DEFAULT_IDENTITY = """# IDENTITY: Core Directives & Style
- **Name**: JARVIS
- **Tone**: Concise, helpful, calm, professional yet warm.
- **Rules**:
  - Keep spoken and chat responses crisp and to the point.
  - Read and update memory notes when learning new facts, preferences, or lessons.
  - Ask for confirmation before running destructive shell commands or overwriting critical files if safe mode is enabled.
"""

DEFAULT_MEMORY = """# MEMORY: Long-term Facts & User Preferences
- **User**: The creator and operator of this machine.
- **Environment**: Windows local AI setup running Ollama.
- **Agent Stack**: Memory Vault, Backtalk Voice, 3D Visualizer Face.
"""

DEFAULT_LESSONS = """# LESSONS: Insights & Learned Patterns
- Always check that local services (Ollama) are reachable before executing heavy models.
- When answering out loud or in voice mode, keep answers to 1-3 crisp sentences.
"""

class VaultManager:
    def __init__(self, vault_dir: str | Path | None = None):
        if vault_dir is None:
            # Default to ~/agent-vault or local vault/ directory
            home_vault = Path.home() / "agent-vault"
            self.vault_dir = home_vault
        else:
            self.vault_dir = Path(vault_dir).expanduser().resolve()
        
        self.ensure_vault()

    def ensure_vault(self):
        """Ensure vault directory and default template files exist."""
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        
        defaults = {
            "SOUL.md": DEFAULT_SOUL,
            "IDENTITY.md": DEFAULT_IDENTITY,
            "MEMORY.md": DEFAULT_MEMORY,
            "LESSONS.md": DEFAULT_LESSONS,
        }
        
        for filename, content in defaults.items():
            file_path = self.vault_dir / filename
            if not file_path.exists():
                try:
                    file_path.write_text(content.strip() + "\n", encoding="utf-8")
                except Exception as e:
                    print(f"[vault] Error creating {filename}: {e}")

    def list_notes(self) -> list[dict]:
        """List all markdown notes in the vault."""
        notes = []
        if not self.vault_dir.exists():
            return notes
        for p in self.vault_dir.glob("*.md"):
            try:
                stat = p.stat()
                notes.append({
                    "name": p.name,
                    "path": str(p),
                    "size": stat.st_size,
                    "modified": stat.st_mtime
                })
            except Exception:
                pass
        return sorted(notes, key=lambda x: x["name"])

    def read_note(self, note_name: str) -> str:
        """Read content of a note by filename."""
        if not note_name.endswith(".md"):
            note_name += ".md"
        file_path = self.vault_dir / note_name
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
        return ""

    def write_note(self, note_name: str, content: str) -> bool:
        """Write/overwrite content of a note."""
        if not note_name.endswith(".md"):
            note_name += ".md"
        file_path = self.vault_dir / note_name
        try:
            file_path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            print(f"[vault] Error writing {note_name}: {e}")
            return False

    def append_note(self, note_name: str, entry: str) -> bool:
        """Append a bullet or text entry to a note."""
        if not note_name.endswith(".md"):
            note_name += ".md"
        file_path = self.vault_dir / note_name
        try:
            current = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
            if current and not current.endswith("\n"):
                current += "\n"
            current += f"- {entry.strip()}\n"
            file_path.write_text(current, encoding="utf-8")
            return True
        except Exception as e:
            print(f"[vault] Error appending to {note_name}: {e}")
            return False

    def get_system_context(self) -> str:
        """Compile core vault notes into a cohesive system prompt context."""
        parts = []
        for name in ["SOUL.md", "IDENTITY.md", "MEMORY.md", "LESSONS.md"]:
            content = self.read_note(name)
            if content:
                parts.append(f"=== {name} ===\n{content.strip()}")
        return "\n\n".join(parts)

    def search_notes(self, query: str) -> list[dict]:
        """Simple keyword search across notes."""
        results = []
        q = query.lower()
        for p in self.vault_dir.glob("*.md"):
            try:
                text = p.read_text(encoding="utf-8")
                if q in text.lower():
                    # Find matching lines
                    matches = [line.strip() for line in text.splitlines() if q in line.lower()]
                    results.append({
                        "note": p.name,
                        "matches": matches[:5]
                    })
            except Exception:
                pass
        return results

if __name__ == "__main__":
    vm = VaultManager()
    print(f"Vault initialized at: {vm.vault_dir}")
    print("Notes:", [n["name"] for n in vm.list_notes()])
