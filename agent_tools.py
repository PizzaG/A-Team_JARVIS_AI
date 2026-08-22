"""
agent_tools.py - Local agent tool registry, schemas, and safe execution engine.
"""
import os
import subprocess
import json
from pathlib import Path
from vault_manager import VaultManager

# Tool schemas compatible with Ollama and OpenAI function calling standards
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a text or code file at the given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file (absolute or relative to current workspace)."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write or overwrite content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to create or overwrite."
                    },
                    "content": {
                        "type": "string",
                        "description": "The exact text content to write."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a specific substring in a file with new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to edit."
                    },
                    "target": {
                        "type": "string",
                        "description": "The exact string to find and replace."
                    },
                    "replacement": {
                        "type": "string",
                        "description": "The replacement string."
                    }
                },
                "required": ["path", "target", "replacement"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and subdirectories in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list (defaults to current directory '.')."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell/PowerShell command on the local machine and get standard output and error.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command line to execute."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Search the persistent memory vault for notes and past lessons.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword or concept to search for in memory."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "append_memory",
            "description": "Save a new fact, preference, or lesson into the agent's memory vault.",
            "parameters": {
                "type": "object",
                "properties": {
                    "note_name": {
                        "type": "string",
                        "description": "The note to append to: MEMORY.md, LESSONS.md, or PEOPLE.md"
                    },
                    "entry": {
                        "type": "string",
                        "description": "The knowledge or lesson item to record."
                    }
                },
                "required": ["note_name", "entry"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "present_on_board",
            "description": "Present an enlarged spotlight card, note, or diagram onto the Barehands glass air board.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Card title to display on the glass."
                    },
                    "body": {
                        "type": "string",
                        "description": "Text or markdown content to display on the glass."
                    }
                },
                "required": ["title", "body"]
            }
        }
    }
]

GATED_TOOLS = {"write_file", "edit_file", "run_command"}

class ToolEngine:
    def __init__(self, workspace_dir: str | Path | None = None, vault: VaultManager | None = None):
        self.workspace_dir = Path(workspace_dir or os.getcwd()).resolve()
        self.vault = vault or VaultManager()

    def is_gated(self, tool_name: str) -> bool:
        return tool_name in GATED_TOOLS

    def execute(self, tool_name: str, args: dict) -> dict:
        """Execute a tool and return result dictionary with 'status' and 'output'."""
        try:
            handler = getattr(self, f"_tool_{tool_name}", None)
            if not handler:
                return {"status": "error", "output": f"Unknown tool: {tool_name}"}
            res = handler(**args)
            return {"status": "success", "output": res}
        except Exception as e:
            return {"status": "error", "output": f"Error executing {tool_name}: {str(e)}"}

    def _resolve_path(self, path_str: str) -> Path:
        p = Path(path_str).expanduser()
        if not p.is_absolute():
            p = (self.workspace_dir / p).resolve()
        return p

    def _tool_read_file(self, path: str) -> str:
        p = self._resolve_path(path)
        if not p.exists():
            return f"Error: File not found: {p}"
        if not p.is_file():
            return f"Error: Path is not a file: {p}"
        try:
            return p.read_text(encoding="utf-8", errors="replace")[:10000]
        except Exception as e:
            return f"Error reading file: {e}"

    def _tool_write_file(self, path: str, content: str) -> str:
        p = self._resolve_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {p.name}"

    def _tool_edit_file(self, path: str, target: str, replacement: str) -> str:
        p = self._resolve_path(path)
        if not p.exists():
            return f"Error: File not found: {p}"
        text = p.read_text(encoding="utf-8")
        if target not in text:
            return f"Error: Target text not found in {p.name}"
        new_text = text.replace(target, replacement, 1)
        p.write_text(new_text, encoding="utf-8")
        return f"Successfully edited {p.name}"

    def _tool_list_directory(self, path: str = ".") -> str:
        p = self._resolve_path(path)
        if not p.exists():
            return f"Error: Directory not found: {p}"
        items = []
        for child in sorted(p.iterdir()):
            kind = "DIR " if child.is_dir() else "FILE"
            size = f"{child.stat().st_size}B" if child.is_file() else ""
            items.append(f"{kind}  {child.name:30} {size}")
        return "\n".join(items) if items else "(empty directory)"

    def _tool_run_command(self, command: str) -> str:
        res = subprocess.run(
            command,
            shell=True,
            cwd=str(self.workspace_dir),
            capture_output=True,
            text=True,
            timeout=30
        )
        out = res.stdout.strip()
        err = res.stderr.strip()
        if res.returncode != 0:
            return f"Exit code {res.returncode}\nSTDOUT:\n{out}\nSTDERR:\n{err}"
        return out if out else "(command executed successfully with no output)"

    def _tool_search_memory(self, query: str) -> str:
        results = self.vault.search_notes(query)
        if not results:
            return f"No memory entries found matching '{query}'."
        lines = []
        for r in results:
            lines.append(f"[{r['note']}]")
            for m in r['matches']:
                lines.append(f"  - {m}")
        return "\n".join(lines)

    def _tool_append_memory(self, note_name: str, entry: str) -> str:
        ok = self.vault.append_note(note_name, entry)
        if ok:
            return f"Recorded memory in {note_name}: '{entry}'"
        return f"Failed to record memory in {note_name}"

    def _tool_present_on_board(self, title: str, body: str) -> str:
        try:
            import urllib.request
            req_data = json.dumps({"a": "present", "title": title, "body": body}).encode("utf-8")
            req = urllib.request.Request("http://127.0.0.1:8794/cmd", data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status in (200, 204):
                    return f"Successfully presented '{title}' onto the Barehands glass air board."
                return f"Board returned status {resp.status}"
        except Exception as e:
            return f"Could not reach Barehands board on http://127.0.0.1:8794 (is Barehands server running?): {e}"

if __name__ == "__main__":
    engine = ToolEngine()
    print("Listing dir:", engine.execute("list_directory", {"path": "."}))
