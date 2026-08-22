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

DEFAULTS = {
    "name": "JARVIS",
    "badge": "LOCAL-AI",
    "face": "board",
    "port": 8790,
    "bus_dir": str(ROOT_DIR / "backtalk"),
    "thinking_sound": False,
    "model": "qwen2.5-coder:14b",
    "ollama_url": "http://127.0.0.1:11434",
    "permission_mode": "ask"
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
        bt_cfg_file.write_text(json.dumps(bt_data, indent=2), encoding="utf-8")
    except Exception:
        pass
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
    if now - WEB_STATE["last_update"] < 1.5 and WEB_STATE["state"] in ("speaking", "thinking", "listening"):
        t = now
        samples = [0.0] * 64
        level = WEB_STATE["level"]
        if WEB_STATE["state"] == "speaking":
            if level <= 0.0:
                level = 0.5 + 0.3 * math.sin(t * 8.0)
            samples = [
                (math.sin(i * 0.55 + t * 9.0) * 0.6 + math.sin(i * 1.7 - t * 13.0) * 0.4)
                * 9000.0 * (0.35 + 0.65 * abs(math.sin(t * 2.6)))
                for i in range(64)
            ]
        return {
            "state": WEB_STATE["state"],
            "level": level,
            "samples": samples,
            "alert": False,
            "loading": WEB_STATE["state"] == "thinking"
        }

    state = "idle"
    try:
        state = (BUS / ".voice_state").read_text(encoding="utf-8").strip().lower()
        if state not in STATES:
            state = "idle"
    except OSError:
        pass

    level = 0.0
    samples = [0.0] * 64
    try:
        payload = json.loads((BUS / ".voice_waveform").read_text(encoding="utf-8"))
        age = time.time() - float(payload.get("ts", 0))
        raw = payload.get("samples") or []
        if raw and age < WAVEFORM_STALE_S:
            state = "speaking"
            samples = [float(s) for s in raw[:64]]
            mean = sum(abs(s) for s in samples) / len(samples)
            level = min(1.0, mean / 3000.0)
    except Exception:
        pass

    loading = (BUS / ".voice_loading_pid").exists() if BUS.exists() else False
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

class UnifiedHandler(BaseHTTPRequestHandler):
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
                self._send_json(read_bus())
            elif url_path == "/config":
                cfg = load_config()
                out = {
                    "name": cfg["name"],
                    "badge": cfg["badge"],
                    "face": cfg["face"],
                    "model": cfg["model"],
                    "permission_mode": cfg["permission_mode"],
                    "thinking_sound": bool(cfg.get("thinking_sound", False)),
                    "faces": list_faces()
                }
                self._send_json(out)
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
            body_raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            data = json.loads(body_raw) if body_raw else {}

            if url_path == "/api/config":
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

            if tool_calls_acc:
                tool_list = list(tool_calls_acc.values())
                CHAT_HISTORY.append({
                    "role": "assistant",
                    "content": accumulated_text or None,
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
        if path == "/":
            path = "/index.html"
        target = (HERE / path.lstrip("/")).resolve()
        if target != HERE and HERE not in target.parents:
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
    url = f"http://127.0.0.1:{PORT}/"
    srv = create_server("0.0.0.0", PORT)
    print(f"Unified Agent Server running on {url} (Ollama Backend) - Ctrl-C to stop", flush=True)
    if "--no-open" not in sys.argv:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
