#!/usr/bin/env python3
"""
Local Jarvis agent.

Input:
    F4 push-to-talk microphone OR direct terminal typing

Pipeline:
    Whisper -> Ollama/Qwen -> local Kokoro TTS
                         -> ai-visualizer/barehands state bus

No Claude, OpenAI, ElevenLabs, or cloud voice services are used.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
import warnings
import sys
import select
import termios
import tty
from pathlib import Path

import requests
import ollama

# Keep the Jarvis console clean: these are benign dependency/model warnings.
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

VOICE_ENABLED = True
sd = None
np = None
WhisperModel = None
pynput_keyboard = None
if VOICE_ENABLED:
    import numpy as np
    import sounddevice as sd
    from faster_whisper import WhisperModel
    from pynput import keyboard as pynput_keyboard
from research_tools import (ResearchError, set_root as set_research_root, root_path, list_files, read_file, search_files, file_info, archive_list, extract_archive, web_search, open_url, download_url)
from agent_tools import JarvisTools
from memory import MemoryVault

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config" / "jarvis.json"
DEFAULT_CONFIG = {
    "name": "JARVIS",
    "ollama": {
        "url": "http://127.0.0.1:11434/api/chat",
        "model": "qwen3.8:27b",
        "temperature": 0.7,
        "max_tokens": 2048,
        "timeout": 300,
        "num_ctx": 32768
    },
    "voice": {
        "whisper_model": "tiny.en",
        "whisper_device": "cpu",
        "whisper_compute_type": "int8",
        "kokoro_voice": "bm_lewis",
        "sample_rate": 24000,
        "speed": 1.10
    },
    "push_to_talk": {
        "key": "f4",
        "sample_rate": 16000
    },
    "research": {"Root": "Project_Folder", "max_results": 50, "internet": True, "max_web_results": 8},
    "visuals": {
        "ai_visualizer_bus": "ai-visualizer",
        "barehands_state": "barehands/state"
    },
    "system_prompt": (
        "You are JARVIS, a capable local desktop AI assistant. "
        "Be concise and direct unless the user asks for detail. "
        "You are running completely locally through Ollama. "
        "Do not claim to have performed an action unless you actually did it."
    )
}

def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if CONFIG_PATH.exists():
        user = json.loads(CONFIG_PATH.read_text())
        def merge(a, b):
            for k, v in b.items():
                if isinstance(v, dict) and isinstance(a.get(k), dict):
                    merge(a[k], v)
                else:
                    a[k] = v
        merge(cfg, user)
    return cfg

CFG = load_config()
VOICE_ENABLED = bool(CFG.get("voice", {}).get("enabled", True))
VISUALS_ENABLED = bool(CFG.get("visuals", {}).get("enabled", True))
HANDS_ENABLED = bool(CFG.get("visuals", {}).get("barehands_enabled", True))
MEMORY_ENABLED = bool(CFG.get("memory", {}).get("enabled", True))
INTERNET_ENABLED = bool(CFG.get("research", {}).get("internet", True))

# Import optional voice dependencies only when voice is enabled.
if VOICE_ENABLED and np is None:
    import numpy as np
    import sounddevice as sd
    from faster_whisper import WhisperModel
    from pynput import keyboard as pynput_keyboard

NAME = CFG["name"]
OLLAMA_URL = CFG["ollama"].get("url", "http://127.0.0.1:11434/api/chat")
MODEL = CFG["ollama"]["model"]
PTT_KEY = CFG["push_to_talk"]["key"]
AUDIO_RATE = int(CFG["push_to_talk"]["sample_rate"])
TTS_RATE = int(CFG["voice"]["sample_rate"])
# Keep enough room for normal conversation + tool results.  Qwen3.x templates
# require a real user turn to remain in the rendered context; an undersized
# context can cause Ollama to trim that turn and return "no user query found".
NUM_CTX = int(CFG["ollama"].get("num_ctx", 32768))

VIS_BUS = ROOT / CFG["visuals"]["ai_visualizer_bus"]
HANDS_STATE = ROOT / CFG["visuals"]["barehands_state"]
RESEARCH_ROOT = set_research_root(CFG.get("research", {}).get("Root", CFG.get("research", {}).get("root", "Project_Folder")))
PROJECT_ROOT = RESEARCH_ROOT
MEMORY_ROOT = ROOT / CFG.get("memory", {}).get("Root", "Memory_Vault")
if not MEMORY_ROOT.is_absolute():
    MEMORY_ROOT = ROOT / MEMORY_ROOT
MEMORY = MemoryVault(MEMORY_ROOT)
TOOLS = JarvisTools(PROJECT_ROOT, MEMORY)
if VISUALS_ENABLED:
    VIS_BUS.mkdir(parents=True, exist_ok=True)
if HANDS_ENABLED:
    HANDS_STATE.mkdir(parents=True, exist_ok=True)

running = True
recording = []
recording_lock = threading.Lock()
is_recording = False
audio_stop = threading.Event()
interaction_lock = threading.Lock()

def set_state(state: str):
    """Drive Jared's existing visualizer and barehands state buses."""
    if state not in ("idle", "listening", "thinking", "speaking"):
        state = "idle"
    if VISUALS_ENABLED:
        (VIS_BUS / ".voice_state").write_text(state, encoding="utf-8")
    if HANDS_ENABLED:
        (HANDS_STATE / "state").write_text(state, encoding="utf-8")
    if state != "speaking":
        clear_wave()


def write_wave(samples):
    """Publish normalized waveform data to both visual components."""
    vals = [max(0.0, min(1.0, float(x))) for x in samples[:64]]
    payload = {"ts": time.time(), "samples": vals}
    if VISUALS_ENABLED:
        (VIS_BUS / ".voice_waveform").write_text(json.dumps(payload), encoding="utf-8")
    if HANDS_ENABLED:
        (HANDS_STATE / "wave.json").write_text(json.dumps(payload), encoding="utf-8")


def clear_wave():
    paths = []
    if VISUALS_ENABLED:
        paths.append(VIS_BUS / ".voice_waveform")
    if HANDS_ENABLED:
        paths.append(HANDS_STATE / "wave.json")
    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass

def check_ollama():
    from urllib.parse import urlsplit
    parts = urlsplit(OLLAMA_URL)
    base = f"{parts.scheme}://{parts.netloc}"
    try:
        r = requests.get(base + "/api/tags", timeout=5)
        r.raise_for_status()
        names = {m.get("name") for m in r.json().get("models", [])}
        if MODEL not in names:
            print(f"[WARN] Ollama is running but {MODEL!r} was not found.")
            print(f"       Run: ollama pull {MODEL}")
            return False
        return True
    except Exception as e:
        print(f"[ERROR] Cannot reach Ollama at {base}: {e}")
        return False

whisper = None
if VOICE_ENABLED:
    #print(f"Loading local Whisper model: {CFG['voice']['whisper_model']}")
    whisper = WhisperModel(
        CFG["voice"]["whisper_model"],
        device=CFG["voice"]["whisper_device"],
        compute_type=CFG["voice"]["whisper_compute_type"]
    )

kokoro = None
def get_kokoro():
    global kokoro
    if kokoro is None:
        from kokoro import KPipeline
        try:
            from huggingface_hub.utils import logging as hf_logging
            hf_logging.set_verbosity_error()
        except Exception:
            pass
        kokoro = KPipeline(lang_code="b", repo_id="hexgrad/Kokoro-82M")
    return kokoro

memory_boot = MEMORY.load_boot_context() if MEMORY_ENABLED else "Persistent memory is disabled in the current configuration."
PROMPT_FILE = ROOT / "config" / "system_prompt.md"
if PROMPT_FILE.exists():
    BASE_SYSTEM_PROMPT = PROMPT_FILE.read_text(encoding="utf-8")
else:
    BASE_SYSTEM_PROMPT = CFG["system_prompt"]

RUNTIME_CONTEXT = f"""\n\nRUNTIME CONTEXT (AUTHORITATIVE)\n- AI model: {MODEL}\n- AI backend: Ollama (local)\n- Speech recognition: Whisper / {CFG['voice']['whisper_model']}\n- Speech synthesis: Kokoro / {CFG['voice']['kokoro_voice']}\n- Project workspace: {RESEARCH_ROOT}\n- Project tools directory: {RESEARCH_ROOT / 'Tools'}\n- Persistent memory vault: {MEMORY_ROOT}\n- Internet tools: enabled\n\nUse this runtime context directly when the user asks about the current Jarvis setup. Do not call tools to discover these values, and do not claim you lack visibility into them.\n\nPERSISTENT MEMORY BOOT CONTEXT:\n{memory_boot}"""

history = [{"role": "system", "content": BASE_SYSTEM_PROMPT + RUNTIME_CONTEXT}]

def _tool_call_args(call):
    fn = call.get("function", {}) if isinstance(call, dict) else getattr(call, "function", {})
    args = fn.get("arguments", {}) if isinstance(fn, dict) else getattr(fn, "arguments", {})
    if isinstance(args, str):
        try: return json.loads(args)
        except Exception: return {}
    return args or {}

def _tool_call_name(call):
    fn = call.get("function", {}) if isinstance(call, dict) else getattr(call, "function", {})
    return fn.get("name", "") if isinstance(fn, dict) else getattr(fn, "name", "")

def _ollama_chat(messages):
    """Call Ollama through the official Python client.

    The SDK preserves Ollama's assistant tool-call message structure instead
    of rebuilding it by hand. This is important for Qwen multi-step tool
    calling: the exact assistant tool-call message must be appended to the
    conversation before the corresponding tool messages.
    """
    client = ollama.Client(host=OLLAMA_URL.rsplit('/api/chat', 1)[0])
    return client.chat(
        model=MODEL,
        messages=messages,
        tools=TOOLS.definitions(),
        think=CFG["ollama"].get("think", True),
        options={
            "temperature": CFG["ollama"].get("temperature", 0.7),
            "num_predict": CFG["ollama"].get("max_tokens", 4096),
            "num_ctx": NUM_CTX,
        },
    )

def ask_qwen(user_text: str):
    set_state("thinking")
    history.append({"role": "user", "content": user_text})
    try:
        max_rounds = int(CFG["ollama"].get("max_tool_rounds", 20))
        for _ in range(max_rounds):
            response = _ollama_chat(history)
            message = response.message
            calls = message.tool_calls or []

            # IMPORTANT: append Ollama's actual Message object unchanged.
            # Reconstructing tool_calls into a normal dict was the source of
            # the broken multi-step conversation state with this model.
            history.append(message)

            if not calls:
                answer = (message.content or "").strip()
                if MEMORY_ENABLED:
                    MEMORY.record_interaction(user_text, answer)
                if answer:
                    return answer
                return "Qwen returned no response."

            for call in calls:
                name = call.function.name
                args = call.function.arguments or {}
                if CFG.get("display", {}).get("show_tool_activity", False):
                    print(f"🔧 Qwen → {name}", flush=True)
                result = TOOLS.call(name, args)
                history.append({
                    "role": "tool",
                    "tool_name": name,
                    "content": str(result),
                })

        raise RuntimeError("Qwen exceeded the maximum tool-call rounds without producing a final answer.")
    except Exception as e:
        # Do not leave a half-finished tool-call exchange in history. If a
        # tool/API failure occurs, reset this turn back to the last clean
        # user boundary so the next request cannot inherit a broken loop.
        while history and history[-1] is not None:
            item = history[-1]
            role = item.get("role") if isinstance(item, dict) else getattr(item, "role", None)
            if role == "user":
                history.pop()
                break
            history.pop()
        return f"Local Qwen error: {e}"

_sentence_re = re.compile(r"(.+?[.!?](?:\s+|$)|.+$)", re.S)

def normalize_for_speech(text: str) -> str:
    """Turn technical/markdown-heavy text into natural spoken English.

    This changes only the audio narration; the terminal still shows Qwen's
    original answer. It avoids reading markdown punctuation, units, URLs,
    code formatting, and common technical abbreviations literally.
    """
    s = str(text)
    # Markdown headings/emphasis/code markers.
    s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s, flags=re.M)
    s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
    s = re.sub(r"__(.*?)__", r"\1", s)
    s = re.sub(r"(?<!\*)\*(?!\*)", "", s)
    s = s.replace("`", "")
    # Markdown links: keep the visible label, not the URL.
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    # Common storage/network units. Do this before punctuation cleanup.
    units = {
        r"(?i)(?<=\d)\s*tb\b": " terabytes",
        r"(?i)(?<=\d)\s*gb\b": " gigabytes",
        r"(?i)(?<=\d)\s*mb\b": " megabytes",
        r"(?i)(?<=\d)\s*kb\b": " kilobytes",
        r"(?i)(?<=\d)\s*b\b": " bytes",
        r"(?i)(?<=\d)\s*mhz\b": " megahertz",
        r"(?i)(?<=\d)\s*ghz\b": " gigahertz",
        r"(?i)(?<=\d)\s*ms\b": " milliseconds",
        r"(?i)(?<=\d)\s*mbps\b": " megabits per second",
        r"(?i)(?<=\d)\s*gbps\b": " gigabits per second",
    }
    for pat, repl in units.items():
        s = re.sub(pat, repl, s)
    # A/B and common technical notation should sound natural.
    s = re.sub(r"\bA/B\b", "A B", s, flags=re.I)
    s = re.sub(r"\bI/O\b", "input output", s, flags=re.I)
    s = re.sub(r"\bUFS\b", "U F S", s, flags=re.I)
    s = re.sub(r"\bAPN\b", "A P N", s, flags=re.I)
    # Don't make Kokoro read URLs, hashes, or shell punctuation character-by-character.
    s = re.sub(r"https?://\S+", "the linked page", s)
    s = re.sub(r"\b[0-9a-f]{32,64}\b", "the file hash", s, flags=re.I)
    s = re.sub(r"[|]", ", ", s)
    # Bullets, table separators and repeated punctuation become pauses.
    s = re.sub(r"^\s*[-+•]\s+", "", s, flags=re.M)
    s = re.sub(r"-{3,}", ". ", s)
    s = re.sub(r"={3,}", ". ", s)
    # Collapse whitespace while preserving sentence breaks.
    s = re.sub(r"\s+", " ", s).strip()
    return s

def sentences(text):
    return [x.strip() for x in _sentence_re.findall(text) if x.strip()]

def speak(text: str):
    """Generate and play Kokoro audio locally, sentence by sentence."""
    if not text:
        return
    pipe = get_kokoro()
    spoken_text = normalize_for_speech(text) if CFG["voice"].get("speech_normalization", True) else text
    set_state("speaking")
    try:
        for sentence in sentences(spoken_text):
            if not running:
                break
            for _, _, audio in pipe(
                sentence,
                voice=CFG["voice"]["kokoro_voice"],
                speed=float(CFG["voice"].get("speed", 1.08)),
                split_pattern=r"\n+"
            ):
                if not running:
                    break
                arr = np.asarray(audio, dtype=np.float32)
                if len(arr):
                    idx = np.linspace(0, len(arr)-1, 64).astype(int)
                    vals = np.abs(arr[idx])
                    peak = max(float(vals.max()), 1e-6)
                    write_wave((vals / peak).clip(0, 1))
                sd.play(arr, TTS_RATE, blocking=True)
                clear_wave()
    finally:
        clear_wave()
        set_state("idle")

def transcribe(audio):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    try:
        import scipy.io.wavfile as wav
        wav.write(path, AUDIO_RATE, audio)
        segments, _ = whisper.transcribe(path, beam_size=5, vad_filter=True)
        return " ".join(s.text.strip() for s in segments).strip()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

def mic_callback(indata, frames, time_info, status):
    if is_recording:
        with recording_lock:
            recording.append(indata.copy())

def on_press(key):
    global is_recording, recording
    try:
        wanted = getattr(pynput_keyboard.Key, PTT_KEY)
    except AttributeError:
        wanted = pynput_keyboard.Key.f4
    if key == wanted and not is_recording:
        is_recording = True
        with recording_lock:
            recording = []
        set_state("listening")
        print("\n🎤 Listening...", end="", flush=True)

def on_release(key):
    global is_recording
    try:
        wanted = getattr(pynput_keyboard.Key, PTT_KEY)
    except AttributeError:
        wanted = pynput_keyboard.Key.f4
    if key == wanted and is_recording:
        is_recording = False

def format_for_display(text: str) -> str:
    """Make Qwen's Markdown-friendly answer readable in a plain terminal.

    Qwen still receives and retains its original response. This only cleans
    the user-facing terminal copy so Markdown tables, emphasis markers, and
    headings do not turn into visually noisy raw syntax.
    """
    s = str(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = s.split("\n")
    out = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if out and out[-1] != "":
                out.append("")
            continue

        # Convert Markdown table rows into simple readable lines.
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if cells and all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                continue
            if len(cells) >= 2:
                if not out:
                    out.append(f"{cells[0]}: {cells[1]}")
                else:
                    out.append(f"- {cells[0]}: {cells[1]}")
                continue

        line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)
        line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
        line = re.sub(r"__(.*?)__", r"\1", line)
        line = re.sub(r"(?<!\*)\*(?!\*)", "", line)
        line = line.replace("`", "")
        line = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"\s+", " ", line).strip()
        out.append(line)

    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)

def process_text(text: str):
    text = text.strip()
    if not text:
        return
    with interaction_lock:
        # The terminal runs in raw mode. Clear the current prompt line before
        # printing a response so wrapped input cannot shift the output sideways.
        if sys.stdin.isatty():
            sys.stdout.write("\r\033[2K\r")
            sys.stdout.flush()
        print(f"🗣️  You: {text}")
        answer = ask_qwen(text)
        print(f"🤖 {NAME}: {format_for_display(answer)}")
        speak(answer)
        if running and sys.stdin.isatty():
            sys.stdout.write("\n⌨️  You: ")
            sys.stdout.flush()

def terminal_input_loop():
    """Read typed input while consuming F4 terminal escape sequences.

    The global pynput listener handles F4 for push-to-talk. Linux terminals
    also emit F4 as an escape sequence (typically ESC O S). While recording,
    this thread deliberately drains stdin so those bytes can never reach the
    terminal echo path. This is more reliable than trying to parse a partial
    function-key sequence after it has already started arriving.
    """
    if not sys.stdin.isatty():
        while running:
            try:
                text = input("\n⌨️  You: ").strip()
            except (EOFError, KeyboardInterrupt):
                return
            if text:
                process_text(text)
        return

    fd = sys.stdin.fileno()
    old_attrs = termios.tcgetattr(fd)
    line = bytearray()
    try:
        tty.setraw(fd)
        # Raw mode disables normal terminal output processing.
        # Restore newline handling so every \n returns to column zero.
        attrs = termios.tcgetattr(fd)
        attrs[1] |= termios.OPOST
        attrs[1] |= termios.ONLCR
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        # Raw mode disables terminal echo; we explicitly echo ordinary text.
        sys.stdout.write("\n⌨️  You: ")
        sys.stdout.flush()

        while running:
            # While F4 is down, consume everything the terminal sends. This
            # includes repeated ESC O S / ESC [ O S sequences generated by F4.
            if is_recording:
                ready, _, _ = select.select([fd], [], [], 0.02)
                if ready:
                    try:
                        os.read(fd, 256)
                    except OSError:
                        pass
                continue

            ready, _, _ = select.select([fd], [], [], 0.05)
            if not ready:
                continue

            try:
                data = os.read(fd, 256)
            except OSError:
                break
            if not data:
                break

            i = 0
            while i < len(data):
                b = data[i]

                # If an escape sequence starts outside recording, consume the
                # complete function-key sequence without echoing it. F4 is
                # handled by pynput, so nothing from it belongs in the prompt.
                if b == 0x1b:
                    i += 1
                    # Consume up to a short CSI/SS3 sequence from this chunk.
                    if i < len(data) and data[i] in (ord('O'), ord('[')):
                        prefix = data[i]
                        i += 1
                        while i < len(data) and i < len(data) + 4:
                            c = data[i]
                            i += 1
                            if 0x40 <= c <= 0x7e:
                                break
                    continue

                if b in (10, 13):
                    text = line.decode("utf-8", errors="replace").strip()
                    line.clear()
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    if text:
                        process_text(text)
                    continue

                if b in (8, 127):
                    if line:
                        line.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                    i += 1
                    continue

                # Ignore other terminal control bytes; echo ordinary bytes.
                if b >= 32 or b >= 128:
                    line.append(b)
                    try:
                        os.write(sys.stdout.fileno(), bytes([b]))
                    except OSError:
                        pass
                i += 1

    except (OSError, EOFError, KeyboardInterrupt):
        return
    finally:
        try:
            termios.tcflush(fd, termios.TCIFLUSH)
        except Exception:
            pass
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)

def main():
    global running, is_recording
    print(f"\n=== {NAME} — LOCAL MODE ===")
    print(f"Brain : Ollama / {MODEL}")
    print(f"Ears  : Whisper / {CFG['voice']['whisper_model']}")
    print(f"Mouth : Kokoro / {CFG['voice']['kokoro_voice']}")
    face_name = CFG.get("visuals", {}).get("face", "board")
    print(f"Face Name  : {face_name.capitalize()}" if VISUALS_ENABLED else "Face Name  : Disabled")
    print("Hands Addon : Enabled" if HANDS_ENABLED else "Hands Addon : Disabled")
    face_url = os.environ.get("FACE_URL", "")
    print(f"Face Link  : {face_url}" if VISUALS_ENABLED else "Face Link  : Disabled")
    hands_url = os.environ.get("HANDS_URL", "")
    print(f"Hands Link : {hands_url}" if HANDS_ENABLED else "Hands Link : Disabled")
    print("Loading Persistent Memory ...")
    print("✓ Local Memory Vault Ready", flush=True)
    check_ollama()
    if VOICE_ENABLED:
        print("Loading Kokoro Voice Engine ...", flush=True)
        try:
            get_kokoro()
            print("✓ Local Kokoro Ready", flush=True)
        except Exception as e:
            print(f"[ERROR] Kokoro initialization failed: {e}", flush=True)
            print("       Jarvis will continue, but spoken replies will be unavailable until Kokoro is fixed.", flush=True)
    set_state("idle")
    print(f"Project Root  : {RESEARCH_ROOT}")
    print(f"Memory Vault  : {MEMORY_ROOT}" if MEMORY_ENABLED else "Memory Vault  : Disabled")

    if VOICE_ENABLED:
        print(f"\nHold [{PTT_KEY.upper()}] To Talk & Release [{PTT_KEY.upper()}] To Send.")
        print("Or Type Directly Into The ⌨️ Prompt. You Can Use Either Input Method.\n")
        listener = pynput_keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
    else:
        print("\nVoice Input Disabled. Type Directly Into The ⌨️ Prompt.\n")
        listener = None
    threading.Thread(target=terminal_input_loop, daemon=True, name="jarvis-terminal").start()

    try:
        while running:
            if VOICE_ENABLED and is_recording:
                with sd.InputStream(
                    samplerate=AUDIO_RATE, channels=1,
                    dtype="float32", callback=mic_callback
                ):
                    while is_recording and running:
                        sd.sleep(50)
                with recording_lock:
                    chunks = list(recording)
                if not chunks:
                    set_state("idle")
                    continue
                audio = np.concatenate(chunks, axis=0).reshape(-1)
                print(" Processing...", end="", flush=True)
                text = transcribe(audio)
                if not text:
                    print("\n❌ I didn't catch that.")
                    set_state("idle")
                    continue
                process_text(text)
            else:
                sd.sleep(50)
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        set_state("idle")
        clear_wave()
        if listener is not None:
            listener.stop()
        if sd is not None:
            sd.stop()
        print("\nJarvis stopped.")

if __name__ == "__main__":
    main()
