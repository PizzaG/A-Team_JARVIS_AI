"""
Verification script for Fullstack Local AI Agent.
"""
import asyncio
import json
import urllib.request
import time
from vault_manager import VaultManager
from agent_tools import ToolEngine

def test_vault():
    print("--- Testing Vault Manager ---")
    vm = VaultManager()
    notes = vm.list_notes()
    print(f"Vault located at: {vm.vault_dir}")
    print(f"Found {len(notes)} notes: {[n['name'] for n in notes]}")
    soul = vm.read_note("SOUL.md")
    assert len(soul) > 0, "SOUL.md should not be empty"
    print("Vault test passed!\n")

def test_tools():
    print("--- Testing Agent Tools ---")
    engine = ToolEngine()
    
    # 1. list_directory
    res = engine.execute("list_directory", {"path": "."})
    print("list_directory output:", res['status'], f"({len(res['output'])} chars)")
    assert res['status'] == "success"
    
    # 2. search_memory
    res_mem = engine.execute("search_memory", {"query": "JARVIS"})
    print("search_memory output:", res_mem['status'], f"({len(res_mem['output'])} chars)")
    assert res_mem['status'] == "success"
    
    # 3. run_command
    res_cmd = engine.execute("run_command", {"command": "echo JARVIS ONLINE"})
    print("run_command output:", res_cmd['status'], res_cmd['output'])
    assert "JARVIS ONLINE" in res_cmd['output']
    print("Tools test passed!\n")

async def test_brain():
    print("--- Testing WarmBrain Streaming with Ollama ---")
    import sys
    sys.path.insert(0, "backtalk")
    from backtalk.brain import WarmBrain
    
    brain = WarmBrain()
    await brain.start()
    print(f"Brain connected to {brain.model}")
    
    sentences = []
    t0 = time.time()
    async for s in brain.ask_stream("Confirm you are running locally and state your name in one sentence."):
        print(f"  [+{time.time()-t0:.2f}s] {s}")
        sentences.append(s)
    await brain.stop()
    assert len(sentences) > 0, "Should have streamed at least 1 sentence"
    print("Brain test passed!\n")

def run_all():
    test_vault()
    test_tools()
    asyncio.run(test_brain())
    print("=== ALL VERIFICATION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_all()
