#!/usr/bin/env python3
# ai-visualizer & Unified Local AI Agent Server.
# Copyright (C) 2026 Jared Rhodenizer, local AI edition.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unified Local AI Server: Serves 3D faces, Web Chat Terminal,
Ollama Model Switcher, Memory Vault Manager, and Visualizer Bus State.
"""
import json
import math
import mimetypes
import os
import re
import sys
import threading
import time
import urllib.request
import urllib.parse
import urllib.error
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT_DIR = HERE.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from vault_manager import VaultManager
    from agent_tools import ToolEngine, TOOL_DEFINITIONS, GATED_TOOLS
except ImportError:
    VaultManager = None
    ToolEngine = None
    TOOL_DEFINITIONS = []
    GATED_TOOLS = set()

STATES = {"idle", "listening", "thinking", "speaking"}
WAVEFORM_STALE_S = 0.6

BAREHANDS_DIR = ROOT_DIR / "barehands"

def load_barehands_config():
    cfg = {"name": "Assistant", "port": 8790, "orbs": []}
    try:
        bh_cfg_file = BAREHANDS_DIR / "barehands.json"
        if bh_cfg_file.exists():
            cfg.update(json.loads(bh_cfg_file.read_text(encoding="utf-8")))
    except Exception:
        pass
    if not cfg.get("orbs"):
        cfg["orbs"] = [
            {"title": "Notes", "path": "sample-notes", "kind": "notes"},
            {"title": "Props", "path": "media", "kind": "media"},
        ]
    for orb in cfg["orbs"]:
        orb["path"] = str(Path(str(orb.get("path", ""))).expanduser())
    return cfg

def orb_root(i):
    """Resolve a notes orb's jail root, or None."""
    try:
        cfg = load_barehands_config()
        orb = cfg["orbs"][int(i)]
        assert orb.get("kind") == "notes"
        p = Path(orb["path"]).expanduser()
        if not p.is_absolute():
            p = (BAREHANDS_DIR / p).resolve()
        return p.resolve()
    except Exception:
        return None

_BAREHANDS_STATE = b"{}"
_CMDS = []
_ALLOWED_CMDS = ("add_img", "add_card", "clear", "reset", "hand", "give",
                 "yank", "hover", "scroll_note", "widget", "explode", "assemble",
                 "present")

# Whisper STT model for browser audio transcription
WHISPER_MODEL = None
WHISPER_LOCK = threading.Lock()

def get_whisper():
    global WHISPER_MODEL
    with WHISPER_LOCK:
        if WHISPER_MODEL is None:
            try:
                from faster_whisper import WhisperModel
                WHISPER_MODEL = WhisperModel("small.en", device="cpu", compute_type="int8")
            except Exception as e:
                print(f"[stt] Warning: could not load faster_whisper: {e}")
                WHISPER_MODEL = False
        return WHISPER_MODEL

DEFAULTS = {
    "name": "JARVIS",
    "badge": "LOCAL-AI",
    "face": "board",
    "port": 8790,
    "bus_dir": str(ROOT_DIR / "backtalk"),
    "thinking_sound": False,
    "model": "qwen2.5-coder:14b",
    "ollama_url": "http://127.0.0.1:11434",
    "permission_mode": "ask",
    "mic_mode": "ptt",
    "ptt_key": "right_alt"
}

def load_config():
    cfg = dict(DEFAULTS)
    cfg_file = HERE / "ai-visualizer.json"
    if cfg_file.exists():
        try:
            user = json.loads(cfg_file.read_text(encoding="utf-8"))
            cfg.update(user)
        except Exception as e:
            print(f"[config] Error reading ai-visualizer.json: {e}")
    
    # Read mic settings from backtalk.json if present
    bt_cfg_file = ROOT_DIR / "backtalk" / "backtalk.json"
    if bt_cfg_file.exists():
        try:
            bt_data = json.loads(bt_cfg_file.read_text(encoding="utf-8"))
            if "mic_mode" in bt_data:
                cfg["mic_mode"] = bt_data["mic_mode"]
            if "ptt_key" in bt_data:
                cfg["ptt_key"] = bt_data["ptt_key"]
            if "permission_mode" in bt_data:
                cfg["permission_mode"] = bt_data["permission_mode"]
        except Exception:
            pass
    return cfg

def save_config(cfg_updates):
    cfg = load_config()
    cfg.update(cfg_updates)
    cfg_file = HERE / "ai-visualizer.json"
    try:
        cfg_file.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[config] Error saving ai-visualizer.json: {e}")
    
    # Also update backtalk.json if present
    bt_cfg_file = ROOT_DIR / "backtalk" / "backtalk.json"
    try:
        bt_data = {}
        if bt_cfg_file.exists():
            bt_data = json.loads(bt_cfg_file.read_text(encoding="utf-8"))
        if "name" in cfg_updates:
            bt_data["name"] = cfg_updates["name"]
        if "model" in cfg_updates:
            bt_data["model"] = cfg_updates["model"]
        if "permission_mode" in cfg_updates:
            bt_data["permission_mode"] = cfg_updates["permission_mode"]
        if "mic_mode" in cfg_updates:
            bt_data["mic_mode"] = cfg_updates["mic_mode"]
        if "ptt_key" in cfg_updates:
            bt_data["ptt_key"] = cfg_updates["ptt_key"]
        # Ensure barehands_state_dir is preserved
        if "barehands_state_dir" not in bt_data:
            bt_data["barehands_state_dir"] = str((ROOT_DIR / "barehands" / "state").resolve())
        bt_cfg_file.write_text(json.dumps(bt_data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[config] Error saving backtalk.json: {e}")
    return cfg

CFG = load_config()
BUS = Path(CFG.get("bus_dir") or HERE).expanduser().resolve()
PORT = int(CFG.get("port", 8790))

# Initialize local vault & tools
vault = VaultManager() if VaultManager else None
tool_engine = ToolEngine(workspace_dir=ROOT_DIR, vault=vault) if ToolEngine else None

# Active visualizer simulation state for web chat
WEB_STATE = {
    "state": "idle",
    "level": 0.0,
    "samples": [0.0] * 64,
    "last_update": time.time()
}

def set_web_state(state_name, level=0.0):
    WEB_STATE["state"] = state_name
    WEB_STATE["level"] = level
    WEB_STATE["last_update"] = time.time()
    try:
        BUS.mkdir(parents=True, exist_ok=True)
        (BUS / ".voice_state").write_text(state_name, encoding="utf-8")
    except Exception:
        pass

def list_faces():
    faces = []
    fdir = HERE / "faces"
    if fdir.is_dir():
        for p in sorted(fdir.iterdir()):
            if p.is_dir() and (p / "index.html").exists():
                meta = {"id": p.name, "title": p.name.title(), "tagline": ""}
                try:
                    meta.update(json.loads((p / "face.json").read_text(encoding="utf-8")))
                except Exception:
                    pass
                meta["id"] = p.name
                faces.append(meta)
    return faces

def read_bus():
    now = time.time()

    state = "idle"
    level = 0.0
    samples = [0.0] * 64
    loading = False

    # 1. Check Backtalk bus state (.voice_state)
    try:
        if (BUS / ".voice_state").exists():
            st = (BUS / ".voice_state").read_text(encoding="utf-8").strip().lower()
            if st in STATES:
                state = st
    except OSError:
        pass

    # 2. Check Barehands state (barehands/state/state)
    if state == "idle":
        try:
            bh_state_file = ROOT_DIR / "barehands" / "state" / "state"
            if bh_state_file.exists():
                st = bh_state_file.read_text(encoding="utf-8").strip().lower()
                if st in STATES:
                    state = st
        except Exception:
            pass

    # 3. Check Backtalk waveform (.voice_waveform)
    try:
        if (BUS / ".voice_waveform").exists():
            payload = json.loads((BUS / ".voice_waveform").read_text(encoding="utf-8"))
            age = now - float(payload.get("ts", 0))
            raw = payload.get("samples") or []
            if raw and age < WAVEFORM_STALE_S:
                state = "speaking"
                samples = [float(s) for s in raw[:64]]
                mean = sum(abs(s) for s in samples) / len(samples)
                level = min(1.0, mean / 3000.0)
    except Exception:
        pass

    # 4. Check Barehands waveform (barehands/state/wave.json)
    if state != "speaking":
        try:
            bh_wave_file = ROOT_DIR / "barehands" / "state" / "wave.json"
            if bh_wave_file.exists():
                payload = json.loads(bh_wave_file.read_text(encoding="utf-8"))
                age = now - float(payload.get("ts", 0))
                raw = payload.get("samples") or []
                if raw and age < WAVEFORM_STALE_S:
                    state = "speaking"
                    samples = [float(s) * 9000.0 for s in raw[:64]]
                    level = min(1.0, sum(abs(s) for s in samples) / len(samples) / 3000.0)
        except Exception:
            pass

    loading = (BUS / ".voice_loading_pid").exists() if BUS.exists() else False

    # 5. Check Web simulation state if bus is idle and web has active state
    if state == "idle" and now - WEB_STATE["last_update"] < 2.5 and WEB_STATE["state"] in ("speaking", "thinking", "listening"):
        state = WEB_STATE["state"]
        level = WEB_STATE["level"]
        t = now
        if state == "speaking":
            if level <= 0.0:
                level = 0.5 + 0.3 * math.sin(t * 8.0)
            samples = [
                (math.sin(i * 0.55 + t * 9.0) * 0.6 + math.sin(i * 1.7 - t * 13.0) * 0.4)
                * 9000.0 * (0.35 + 0.65 * abs(math.sin(t * 2.6)))
                for i in range(64)
            ]
        elif state == "listening":
            level = 0.4 + 0.2 * math.sin(t * 12.0)
            samples = [(math.sin(i * 0.8 + t * 14.0) * 4000.0) for i in range(64)]
        loading = state == "thinking"

    # Fill synthesized samples for active states if bus has no waveform
    if state == "listening" and all(s == 0.0 for s in samples):
        level = 0.4 + 0.2 * math.sin(now * 12.0)
        samples = [(math.sin(i * 0.8 + now * 14.0) * 4000.0) for i in range(64)]

    return {"state": state, "level": level, "samples": samples, "alert": False, "loading": loading}

# Conversation history for web chat
CHAT_HISTORY = []

def get_ollama_models(base_url="http://127.0.0.1:11434"):
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", headers={"User-Agent": "FullStackAgent"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []

def extract_raw_tool_calls(text: str) -> list[dict]:
    if not text:
        return []
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            cleaned = "\n".join(lines[1:-1]).strip()
    if cleaned.startswith("<tool_call>") and cleaned.endswith("</tool_call>"):
        cleaned = cleaned[11:-12].strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "name" in data and ("arguments" in data or "parameters" in data):
            args = data.get("arguments") if "arguments" in data else data.get("parameters", {})
            return [{
                "id": "call_raw_0",
                "type": "function",
                "function": {
                    "name": data["name"],
                    "arguments": json.dumps(args) if isinstance(args, dict) else str(args)
                }
            }]
    except Exception:
        pass

    match = re.search(r'\{\s*"name"\s*:\s*"([a-zA-Z0-9_-]+)"\s*,\s*"(?:arguments|parameters)"\s*:\s*(\{.*?\})\s*\}', text, re.DOTALL)
    if match:
        fn_name = match.group(1)
        raw_args = match.group(2)
        return [{
            "id": "call_raw_0",
            "type": "function",
            "function": {
                "name": fn_name,
                "arguments": raw_args
            }
        }]
    return []

class UnifiedHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence routine 250ms polling HTTP access logs to keep the console clean
        pass

    def do_OPTIONS(self):
        try:
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass

    def do_GET(self):
        url_path = self.path.split("?")[0]
        try:
            if url_path == "/state":
                if "role=render" in self.path or "scene=1" in self.path:
                    self._send_bytes(_BAREHANDS_STATE, "application/json")
                else:
                    self._send_json(read_bus())
            elif url_path == "/config":
                cfg = load_config()
                bh_cfg = load_barehands_config()
                out = {
                    "name": cfg["name"],
                    "badge": cfg["badge"],
                    "face": cfg["face"],
                    "model": cfg["model"],
                    "permission_mode": cfg["permission_mode"],
                    "thinking_sound": bool(cfg.get("thinking_sound", False)),
                    "faces": list_faces(),
                    "mic_mode": cfg.get("mic_mode", "ptt"),
                    "ptt_key": cfg.get("ptt_key", "right_alt"),
                    "orbs": [{"title": o.get("title", "?"), "kind": o.get("kind", "notes")} for o in bh_cfg.get("orbs", [])]
                }
                self._send_json(out)
            elif url_path == "/api/voice-config":
                cfg = load_config()
                self._send_json({
                    "mic_mode": cfg.get("mic_mode", "ptt"),
                    "ptt_key": cfg.get("ptt_key", "right_alt")
                })
            elif url_path == "/orb":
                s_dir = BAREHANDS_DIR / "state"
                out = {"state": "idle", "mood": "green", "wave": None}
                bus_st = read_bus()
                out["state"] = bus_st.get("state", "idle")
                try:
                    m_file = s_dir / "mood.json"
                    if m_file.exists():
                        m = json.loads(m_file.read_text(encoding="utf-8"))
                        if time.time() - float(m.get("ts", 0)) < 45.0:
                            out["mood"] = m.get("mood", "green")
                except Exception:
                    pass
                if out["state"] == "speaking":
                    if bus_st.get("samples"):
                        out["wave"] = [float(s) / 9000.0 for s in bus_st["samples"][:64]]
                    else:
                        try:
                            w_file = s_dir / "wave.json"
                            if w_file.exists():
                                w = json.loads(w_file.read_text(encoding="utf-8"))
                                if time.time() - float(w.get("ts", 0)) < 0.6:
                                    out["wave"] = w.get("samples", [])[:64]
                        except Exception:
                            pass
                self._send_json(out)
            elif url_path.startswith("/tree"):
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                idx = (q.get("orb") or ["0"])[0]
                root = orb_root(idx)
                if root is None or not root.is_dir():
                    self._send_json({"name": "?", "notes": [], "dirs": []}, 404)
                    return

                TEXT_EXTS = {".md", ".txt", ".json", ".py", ".js", ".html", ".css", ".ts", ".sh", ".bat", ".yaml", ".yml", ".toml", ".csv", ".log"}
                SKIP_NAMES = {".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist", ".gemini", ".system_generated", "CLAUDE.md"}

                def walk(d, depth=0):
                    if depth > 4:
                        return {"name": d.name, "notes": [], "dirs": []}
                    out = {"name": d.name, "notes": [], "dirs": []}
                    try:
                        for p in sorted(d.iterdir()):
                            if p.name in SKIP_NAMES or p.name.startswith("."):
                                continue
                            if p.is_dir():
                                sub = walk(p, depth + 1)
                                if sub["notes"] or sub["dirs"]:
                                    out["dirs"].append(sub)
                            elif p.suffix.lower() in TEXT_EXTS:
                                out["notes"].append({
                                    "title": p.name,
                                    "file": f"{int(idx)}/{p.relative_to(root).as_posix()}"
                                })
                    except (PermissionError, OSError):
                        pass
                    return out

                try:
                    tree = walk(root)
                    cfg = load_barehands_config()
                    tree["name"] = cfg["orbs"][int(idx)].get("title", tree["name"])
                    self._send_json(tree)
                except Exception:
                    self._send_json({"name": "?", "notes": [], "dirs": []}, 500)
            elif url_path == "/props":
                EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".webm", ".glb", ".gltf"}
                media_root = (BAREHANDS_DIR / "media").resolve()

                def walkm(d):
                    out = {"name": d.name, "items": [], "dirs": []}
                    for p in sorted(d.iterdir()):
                        if p.name.startswith("."):
                            continue
                        if p.is_dir():
                            sub = walkm(p)
                            if sub["items"] or sub["dirs"]:
                                out["dirs"].append(sub)
                        elif p.suffix.lower() in EXTS:
                            out["items"].append(str(p.relative_to(media_root)).replace("\\", "/"))
                    return out

                try:
                    tree = walkm(media_root)
                    tree["name"] = "Props"
                    self._send_json(tree)
                except Exception:
                    self._send_json({"name": "Props", "items": [], "dirs": []}, 500)
            elif url_path.startswith("/note"):
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                rel = (q.get("f") or [""])[0]
                idx, _, rel = rel.partition("/")
                root = orb_root(idx)
                if root is None:
                    self._send_text("Not found", 404)
                    return
                target = (root / rel).resolve()
                TEXT_EXTS = {".md", ".txt", ".json", ".py", ".js", ".html", ".css", ".ts", ".sh", ".bat", ".yaml", ".yml", ".toml", ".csv", ".log"}
                if (root not in target.parents) or target.suffix.lower() not in TEXT_EXTS or not target.is_file():
                    self._send_text("Not found", 404)
                    return
                try:
                    body = target.read_bytes()
                    self._send_bytes(body, "text/plain; charset=utf-8")
                except Exception:
                    self._send_text("Error reading file", 500)
            elif url_path == "/api/models":
                cfg = load_config()
                models = get_ollama_models(cfg.get("ollama_url", "http://127.0.0.1:11434"))
                self._send_json({"models": models, "current": cfg["model"]})
            elif url_path == "/api/memory":
                if vault:
                    notes = vault.list_notes()
                    self._send_json({"notes": notes, "vault_dir": str(vault.vault_dir)})
                else:
                    self._send_json({"notes": [], "vault_dir": ""})
            elif url_path == "/api/memory/get":
                query = self.path.split("?name=")[-1] if "?name=" in self.path else ""
                name = urllib.parse.unquote(query)
                content = vault.read_note(name) if vault else ""
                self._send_json({"name": name, "content": content})
            elif url_path == "/api/history":
                hist_file = BUS / ".voice_history.json"
                history = []
                if hist_file.exists():
                    try:
                        history = json.loads(hist_file.read_text(encoding="utf-8"))
                    except Exception:
                        history = []
                self._send_json({"history": history})
            else:
                self._static(url_path)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        except Exception as e:
            try:
                self._send_json({"error": str(e)}, 500)
            except Exception:
                pass

    def do_POST(self):
        url_path = self.path.split("?")[0]
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw_bytes = self.rfile.read(length) if length > 0 else b""

            if url_path == "/state":
                global _BAREHANDS_STATE
                _BAREHANDS_STATE = raw_bytes if raw_bytes else b"{}"
                out = json.dumps(_CMDS[:8]).encode("utf-8")
                del _CMDS[:8]
                self._send_bytes(out, "application/json")
                return

            if url_path == "/cmd":
                try:
                    cmd = json.loads(raw_bytes.decode("utf-8")) if raw_bytes else {}
                    assert cmd.get("a") in _ALLOWED_CMDS
                    if cmd["a"] in ("add_img", "hand", "give", "present") and cmd.get("src"):
                        rel = str(cmd.get("src", "")).lstrip("/")
                        if rel.startswith("media/"):
                            rel = rel[6:]
                        media = (BAREHANDS_DIR / "media").resolve()
                        target = (media / rel).resolve()
                        if media not in target.parents or not target.is_file():
                            name = Path(rel).name.lower()
                            hits = [p for p in media.rglob("*")
                                    if p.is_file() and p.name.lower() == name] if name else []
                            if len(hits) != 1:
                                raise ValueError("not in the media airlock")
                            target = hits[0]
                        cmd["src"] = "/media/" + target.relative_to(media).as_posix()
                    _CMDS.append(cmd)
                    self.send_response(204)
                    self.end_headers()
                except Exception:
                    self.send_response(400)
                    self.end_headers()
                return

            if url_path == "/api/transcribe":
                model = get_whisper()
                if not model:
                    self._send_json({"error": "Whisper STT model not available", "text": ""}, 500)
                    return
                try:
                    import io
                    segments, info = model.transcribe(io.BytesIO(raw_bytes), language="en")
                    text = "".join(s.text for s in segments).strip()
                    self._send_json({"text": text, "status": "ok"})
                except Exception as e:
                    self._send_json({"error": str(e), "text": ""}, 500)
                return

            try:
                data = json.loads(raw_bytes.decode("utf-8")) if raw_bytes else {}
            except Exception:
                data = {}

            if url_path in ("/api/config", "/api/voice-config"):
                updated = save_config(data)
                self._send_json({"status": "success", "config": updated})

            elif url_path == "/api/memory/save":
                name = data.get("name", "")
                content = data.get("content", "")
                if vault and name:
                    ok = vault.write_note(name, content)
                    self._send_json({"status": "success" if ok else "error"})
                else:
                    self._send_json({"status": "error", "message": "Vault not initialized"}, 400)

            elif url_path == "/api/chat":
                self._handle_chat_stream(data)

            elif url_path == "/api/state":
                new_st = (data.get("state") or "idle").lower()
                set_web_state(new_st, level=data.get("level", 0.0))
                self._send_json({"status": "ok", "state": new_st})

            elif url_path == "/api/clear":
                global CHAT_HISTORY
                CHAT_HISTORY = []
                set_web_state("idle")
                self._send_json({"status": "cleared"})

            else:
                self._send_json({"error": "Endpoint not found"}, 404)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        except Exception as e:
            try:
                self._send_json({"error": str(e)}, 500)
            except Exception:
                pass

    def _handle_chat_stream(self, data):
        user_message = data.get("message", "").strip()
        model = data.get("model") or CFG.get("model") or "qwen2.5-coder:14b"
        
        if not user_message:
            self._send_json({"error": "Empty message"}, 400)
            return

        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            return

        global CHAT_HISTORY
        if not CHAT_HISTORY and vault:
            sys_ctx = f"You are {CFG.get('name', 'JARVIS')}, a helpful local AI assistant.\n\n{vault.get_system_context()}"
            CHAT_HISTORY.append({"role": "system", "content": sys_ctx})

        CHAT_HISTORY.append({"role": "user", "content": user_message})
        if len(CHAT_HISTORY) > 25:
            CHAT_HISTORY = [CHAT_HISTORY[0]] + CHAT_HISTORY[-20:]

        set_web_state("thinking")
        if not self._sse_send({"type": "state", "state": "thinking"}):
            return

        max_tool_iters = 4
        cur_iter = 0

        while cur_iter < max_tool_iters:
            cur_iter += 1
            payload = {
                "model": model,
                "messages": CHAT_HISTORY,
                "tools": TOOL_DEFINITIONS,
                "stream": True
            }

            req_data = json.dumps(payload).encode("utf-8")
            ollama_url = CFG.get("ollama_url", "http://127.0.0.1:11434")
            req = urllib.request.Request(
                f"{ollama_url}/v1/chat/completions",
                data=req_data,
                headers={"Content-Type": "application/json", "Authorization": "Bearer ollama"}
            )

            accumulated_text = ""
            tool_calls_acc = {}
            is_json_tool_output = False
            streamed_any_text = False

            try:
                with urllib.request.urlopen(req, timeout=60.0) as resp:
                    set_web_state("speaking", 0.6)
                    if not self._sse_send({"type": "state", "state": "speaking"}):
                        set_web_state("idle")
                        return

                    for raw_line in resp:
                        line = raw_line.decode("utf-8").strip()
                        if not line or not line.startswith("data: "):
                            continue
                        chunk_str = line[6:].strip()
                        if chunk_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(chunk_str)
                        except Exception:
                            continue

                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        text = delta.get("content") or ""
                        if text:
                            accumulated_text += text
                            # Check if the output looks like raw JSON tool call
                            if not is_json_tool_output and (accumulated_text.strip().startswith(("{", "```", "<tool_call>"))):
                                is_json_tool_output = True
                            
                            if not is_json_tool_output:
                                streamed_any_text = True
                                if not self._sse_send({"type": "delta", "content": text}):
                                    set_web_state("idle")
                                    return

                        tc_delta = delta.get("tool_calls")
                        if tc_delta:
                            for tc in tc_delta:
                                idx = tc.get("index", 0)
                                if idx not in tool_calls_acc:
                                    tool_calls_acc[idx] = {
                                        "id": tc.get("id", f"call_{idx}"),
                                        "type": "function",
                                        "function": {
                                            "name": tc.get("function", {}).get("name", ""),
                                            "arguments": tc.get("function", {}).get("arguments", "")
                                        }
                                    }
                                else:
                                    if "name" in tc.get("function", {}):
                                        tool_calls_acc[idx]["function"]["name"] += tc["function"]["name"]
                                    if "arguments" in tc.get("function", {}):
                                        tool_calls_acc[idx]["function"]["arguments"] += tc["function"]["arguments"]

            except Exception as e:
                self._sse_send({"type": "error", "error": str(e)})
                set_web_state("idle")
                return

            if not tool_calls_acc and accumulated_text:
                raw_tcs = extract_raw_tool_calls(accumulated_text)
                if raw_tcs:
                    tool_calls_acc = {i: tc for i, tc in enumerate(raw_tcs)}

            if tool_calls_acc:
                tool_list = list(tool_calls_acc.values())
                CHAT_HISTORY.append({
                    "role": "assistant",
                    "content": None if is_json_tool_output else (accumulated_text or None),
                    "tool_calls": tool_list
                })

                for tc in tool_list:
                    fn = tc["function"]
                    fn_name = fn.get("name", "")
                    raw_args = fn.get("arguments", "{}")
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        args = {}

                    if not self._sse_send({"type": "tool_start", "tool": fn_name, "args": args}):
                        set_web_state("idle")
                        return

                    set_web_state("thinking")
                    res = tool_engine.execute(fn_name, args) if tool_engine else {"output": "Tool engine unavailable"}
                    output = str(res.get("output", ""))

                    if not self._sse_send({"type": "tool_end", "tool": fn_name, "output": output}):
                        set_web_state("idle")
                        return

                    CHAT_HISTORY.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", "call_0"),
                        "name": fn_name,
                        "content": output
                    })

                continue
            else:
                if accumulated_text:
                    if is_json_tool_output and not streamed_any_text:
                        self._sse_send({"type": "delta", "content": accumulated_text})
                    CHAT_HISTORY.append({"role": "assistant", "content": accumulated_text})
                break

        set_web_state("idle")
        self._sse_send({"type": "state", "state": "idle"})
        self._sse_send({"type": "done"})

    def _sse_send(self, obj) -> bool:
        try:
            data = f"data: {json.dumps(obj)}\n\n".encode("utf-8")
            self.wfile.write(data)
            self.wfile.flush()
            return True
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            return False

    def _static(self, path):
        if path in ("/", "/index.html"):
            target = HERE / "index.html"
        elif path == "/stage.html":
            target = BAREHANDS_DIR / "stage.html"
        elif path.startswith("/media/"):
            rel = path[7:].lstrip("/")
            target = (BAREHANDS_DIR / "media" / rel).resolve()
            if target != (BAREHANDS_DIR / "media") and (BAREHANDS_DIR / "media") not in target.parents:
                self._send_text("Not found", 404)
                return
        elif path.startswith("/sample-notes/"):
            rel = path[14:].lstrip("/")
            target = (BAREHANDS_DIR / "sample-notes" / rel).resolve()
        else:
            target = (HERE / path.lstrip("/")).resolve()
            if not target.is_file():
                target = (BAREHANDS_DIR / path.lstrip("/")).resolve()
            if (target != HERE and HERE not in target.parents and
                target != BAREHANDS_DIR and BAREHANDS_DIR not in target.parents):
                self._send_text("Not found", 404)
                return

        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            self._send_text("Not found", 404)
            return

        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self._send_bytes(target.read_bytes(), ctype)

    def _send_json(self, obj, code=200):
        try:
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass

    def _send_bytes(self, data, ctype, code=200):
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass

    def _send_text(self, text, code=200):
        self._send_bytes(text.encode("utf-8"), "text/plain", code)

class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def create_server(host, port, max_retries=10):
    for attempt in range(max_retries):
        try:
            return ReusableThreadingHTTPServer((host, port), UnifiedHandler)
        except OSError as e:
            if attempt < max_retries - 1:
                time.sleep(0.5)
            else:
                raise e

if __name__ == "__main__":
    # Pre-warm Whisper STT in background thread so transcriptions are instant
    threading.Thread(target=get_whisper, daemon=True).start()
    url = f"http://127.0.0.1:{PORT}/"
    httpd = create_server("127.0.0.1", PORT)
    print(f"Unified Agent Server running on {url} (Ollama Backend) - Ctrl-C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()
