# backtalk: talk to your Local AI agent out loud.
# Copyright (C) 2026 Jared Rhodenizer, local AI edition.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The warm brain — persistent local LLM session via Ollama with streaming
sentence segmentation and tool execution.

Sentences are yielded the moment they are complete so Kokoro/mouth starts
speaking immediately (~0.5s - 1.5s time-to-first-audio).
"""
import asyncio
import os
import re
import sys
import json
import httpx
from pathlib import Path

# Add parent workspace to sys.path for vault_manager and agent_tools
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from vault_manager import VaultManager
    from agent_tools import ToolEngine, TOOL_DEFINITIONS, GATED_TOOLS
except ImportError:
    # Fallback if running inside backtalk package directory
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from vault_manager import VaultManager
    from agent_tools import ToolEngine, TOOL_DEFINITIONS, GATED_TOOLS

from backtalk.config import CFG, DISCIPLINE
from backtalk.vlog import log

_SENTENCE_END = re.compile(r"(?<=[.!?\n])\s+")
SESSION_FILE = os.path.join(CFG.get("signals_dir") or ".", ".backtalk_session")

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

class WarmBrain:
    def __init__(self, model: str | None = None, can_use_tool=None, resume_id: str | None = None):
        self.model = model or CFG.get("model") or "qwen2.5-coder:14b"
        self._can_use_tool = can_use_tool
        self.session = {"turns": 0, "out_tokens": 0, "in_tokens": 0, "cost": 0.0}
        self._client: httpx.AsyncClient | None = None
        self._resume_id = resume_id
        self._dirty = False
        self._interrupted = False
        
        # Memory vault and tools
        vault_path = CFG.get("extra_dirs", [""])[0] if CFG.get("extra_dirs") else None
        self.vault = VaultManager(vault_path)
        self.tool_engine = ToolEngine(workspace_dir=CFG.get("agent_dir") or ROOT_DIR, vault=self.vault)
        
        self.messages: list[dict] = []

    def _build_system_prompt(self) -> str:
        vault_ctx = self.vault.get_system_context()
        sys_prompt = f"{DISCIPLINE}\n\n=== AGENT IDENTITY & MEMORY ===\n{vault_ctx}"
        return sys_prompt.strip()

    async def start(self):
        base_url = CFG.get("ollama_base_url", "http://127.0.0.1:11434/v1")
        if not base_url.endswith("/v1"):
            base_url = base_url.rstrip("/") + "/v1"
            
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {CFG.get('api_key', 'ollama')}"},
            timeout=httpx.Timeout(60.0, connect=10.0)
        )
        
        self.messages = [
            {"role": "system", "content": self._build_system_prompt()}
        ]
        log(f"[brain] local brain ready (model: {self.model}, base: {base_url})")

    async def set_permission_mode(self, backtalk_mode: str):
        CFG["permission_mode"] = backtalk_mode
        log(f"[brain] permission mode set to: {backtalk_mode}")

    async def context_usage(self):
        return None

    def _remember_session(self, rm=None):
        pass

    def _tally(self, count_turn=True, tokens_out=0, tokens_in=0):
        s = self.session
        if count_turn:
            s["turns"] += 1
        s["out_tokens"] += tokens_out
        s["in_tokens"] += tokens_in

    async def command(self, cmd: str) -> str:
        """Run console slash commands like /clear, /model, /usage."""
        cmd_clean = cmd.strip()
        if cmd_clean == "/clear":
            self.messages = [{"role": "system", "content": self._build_system_prompt()}]
            return "Conversation history cleared."
        elif cmd_clean.startswith("/model"):
            parts = cmd_clean.split(maxsplit=1)
            if len(parts) > 1:
                self.model = parts[1].strip()
                return f"Model switched to {self.model}."
            return f"Current model: {self.model}"
        elif cmd_clean == "/usage":
            s = self.session
            return f"Session: {s['turns']} turns, ~{s['out_tokens']} tokens generated."
        
        # Fallback: normal completion
        if not self._client:
            await self.start()
        try:
            resp = await self._client.post("/chat/completions", json={
                "model": self.model,
                "messages": self.messages + [{"role": "user", "content": cmd_clean}],
                "stream": False
            })
            if resp.status_code == 200:
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return f"error: {resp.status_code} {resp.text}"
        except Exception as e:
            return f"error: {str(e)}"

    async def interrupt(self):
        self._interrupted = True
        self._dirty = False

    async def reset_turn(self, timeout: float = 8.0):
        self._interrupted = False
        self._dirty = False

    async def stop(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def ask_stream(self, utterance: str):
        """Yield complete sentences as they stream out of the local LLM,
        executing any tool calls if requested by the model."""
        if not self._client:
            await self.start()

        self._dirty = True
        self._interrupted = False
        
        self.messages.append({"role": "user", "content": utterance})
        
        # Maintain max context length
        if len(self.messages) > 25:
            # Keep system prompt + recent 20 messages
            self.messages = [self.messages[0]] + self.messages[-20:]

        max_tool_iterations = 4
        current_iter = 0

        while current_iter < max_tool_iterations and not self._interrupted:
            current_iter += 1
            payload = {
                "model": self.model,
                "messages": self.messages,
                "tools": TOOL_DEFINITIONS,
                "stream": True
            }

            accumulated_content = ""
            tool_calls_accumulator = {}
            sentence_buffer = ""

            try:
                async with self._client.stream("POST", "/chat/completions", json=payload) as response:
                    if response.status_code != 200:
                        err_body = await response.aread()
                        yield f"Error from local model: {response.status_code} {err_body.decode('utf-8', errors='replace')}"
                        self._dirty = False
                        return

                    async for raw_line in response.aiter_lines():
                        if self._interrupted:
                            break
                        if not raw_line or not raw_line.startswith("data: "):
                            continue
                        line_data = raw_line[6:].strip()
                        if line_data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(line_data)
                        except json.JSONDecodeError:
                            continue

                        choice = chunk.get("choices", [{}])[0]
                        delta = choice.get("delta", {})

                        # 1. Text streaming
                        text_chunk = delta.get("content") or ""
                        if text_chunk:
                            accumulated_content += text_chunk
                            if not accumulated_content.strip().startswith(("{", "```", "<tool_call>")):
                                sentence_buffer += text_chunk
                                while True:
                                    m = _SENTENCE_END.search(sentence_buffer)
                                    if not m:
                                        break
                                    sentence = sentence_buffer[:m.end()].strip()
                                    sentence_buffer = sentence_buffer[m.end():]
                                    if sentence:
                                        yield sentence

                        # 2. Tool calls delta
                        delta_tools = delta.get("tool_calls")
                        if delta_tools:
                            for tc in delta_tools:
                                idx = tc.get("index", 0)
                                if idx not in tool_calls_accumulator:
                                    tool_calls_accumulator[idx] = {
                                        "id": tc.get("id", f"call_{idx}"),
                                        "type": "function",
                                        "function": {
                                            "name": tc.get("function", {}).get("name", ""),
                                            "arguments": tc.get("function", {}).get("arguments", "")
                                        }
                                    }
                                else:
                                    if "name" in tc.get("function", {}):
                                        tool_calls_accumulator[idx]["function"]["name"] += tc["function"]["name"]
                                    if "arguments" in tc.get("function", {}):
                                        tool_calls_accumulator[idx]["function"]["arguments"] += tc["function"]["arguments"]

                if not tool_calls_accumulator and accumulated_content:
                    raw_tcs = extract_raw_tool_calls(accumulated_content)
                    if raw_tcs:
                        tool_calls_accumulator = {i: tc for i, tc in enumerate(raw_tcs)}

                # Flush remaining sentence buffer if any
                remaining_sentence = sentence_buffer.strip()
                if remaining_sentence and not tool_calls_accumulator:
                    yield remaining_sentence
                elif not tool_calls_accumulator and accumulated_content and not sentence_buffer and not accumulated_content.strip().startswith(("{", "```", "<tool_call>")):
                    yield accumulated_content.strip()

            except Exception as e:
                log(f"[brain] exception during ask_stream: {e}")
                yield f"I ran into an issue connecting to the local model: {str(e)}"
                self._dirty = False
                return

            if self._interrupted:
                self._dirty = False
                return

            # Process tool calls if any
            if tool_calls_accumulator:
                tool_calls_list = list(tool_calls_accumulator.values())
                
                # Append assistant message with tool calls
                self.messages.append({
                    "role": "assistant",
                    "content": accumulated_content or None,
                    "tool_calls": tool_calls_list
                })

                for tc in tool_calls_list:
                    fn = tc["function"]
                    fn_name = fn.get("name", "")
                    raw_args = fn.get("arguments", "{}")
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        args = {}

                    is_gated = self.tool_engine.is_gated(fn_name)
                    approved = True
                    reason = ""

                    # Permission check
                    perm_mode = CFG.get("permission_mode", "ask")
                    if is_gated and perm_mode == "ask" and self._can_use_tool:
                        log(f"[brain] requesting permission for {fn_name} with {args}")
                        perm_res = await self._can_use_tool(fn_name, args)
                        if isinstance(perm_res, bool):
                            approved = perm_res
                        elif isinstance(perm_res, str):
                            approved = (perm_res == "approved" or perm_res == "yes")
                            reason = perm_res

                    if approved:
                        log(f"[brain] executing tool {fn_name} with {args}")
                        res = self.tool_engine.execute(fn_name, args)
                        output_str = str(res.get("output", ""))
                    else:
                        output_str = f"Action rejected by user. Reason: {reason or 'Permission denied'}"
                        log(f"[brain] tool execution denied for {fn_name}")

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", "call_0"),
                        "name": fn_name,
                        "content": output_str
                    })

                # Loop continues to get the model's spoken response following the tool result
                continue
            else:
                # No more tools called, record assistant response in history
                if accumulated_content:
                    self.messages.append({
                        "role": "assistant",
                        "content": accumulated_content
                    })
                    self._tally(count_turn=True, tokens_out=len(accumulated_content.split()))
                break

        self._dirty = False


if __name__ == "__main__":
    import time

    async def demo():
        b = WarmBrain()
        await b.start()
        print("Brain started. Testing prompt...")
        t0 = time.time()
        async for s in b.ask_stream("Hello, who are you and what tools do you have?"):
            print(f"  ({time.time()-t0:4.1f}s) {s}", flush=True)
        await b.stop()

    asyncio.run(demo())
