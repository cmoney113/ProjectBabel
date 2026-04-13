# voice_ai → Bus-Native Refactor Plan

**Baseline LOC:** ~25,000 src (but ~8,000 is real app logic, rest is UI widgets)
**Target:** Gut all HTTP/aiohttp/OmniProxy SDK plumbing, replace with kc-bus.
**Expected result:** Delete ~1,500–2,000 LOC of plumbing, simplify every LLM call to 3 lines.

---

## What Dies

| File | LOC | Why |
|------|-----|-----|
| `src/http_client.py` | 113 | Entire file — aiohttp session manager, completely replaced by bus |
| `src/llm/voice_ai.py` | 345 | VoiceAIService, AsyncClient, Client, all HTTP calls → bus.pub/get |
| `src/llm/translator.py` | ~100 | HTTP calls to OmniProxy → bus.pub/get |
| `src/llm_manager.py` | 108 | Groq HTTP client → bus.pub/get |
| `src/services/voice_ai_service.py` | 360 | Duplicates voice_ai.py — dead already, confirm and delete |

**Total deleted: ~1,000+ LOC of pure plumbing**

---

## What Survives Unchanged

Everything UI (PySide6/QFluentWidgets), ASR, TTS, wbind, porcupine, settings — none of that touches HTTP. It all stays exactly as-is.

| Survives | Why |
|----------|-----|
| `src/workers/voice_ai_worker.py` | Logic is fine, just swap LLM calls |
| `src/pipeline/voice_pipeline.py` | Orchestration logic is fine, swap LLM calls |
| `src/conversation_context.py` | Pure logic, no HTTP |
| `src/tts_manager.py` | TTS is local/subprocess, no HTTP |
| `src/voice_processor.py` | ASR is local, no HTTP |
| All `src/ui/` | Pure UI, no HTTP |
| `src/porcupine_manager.py` | Wake word, no HTTP |
| `src/web_search.py` | Can stay or move to bus — defer |

---

## The Core Change

**Before** (every LLM call):
```python
async with AsyncClient(base_url="http://127.0.0.1:8743") as client:
    response = await client.chat.completions.create(
        model=self.model,
        messages=messages,
        temperature=0.3,
        max_tokens=500,
    )
    content = response.choices[0].message.get("content", "")
```

**After** (every LLM call):
```python
import sys; sys.path.insert(0, os.path.expanduser("~/kernclip/bus/sdk/python"))
from kernclip_bus import Bus
from uuid import uuid4
import json

bus = Bus()
reply = f"llm.omni.response.{uuid4().hex[:8]}"
bus.pub("llm.omni.request", json.dumps({
    "prompt": build_prompt(messages),
    "model": model,
    "reply_to": reply,
}))
content = json.loads(bus.get(reply).data).get("text", "")
```

That's it. No session management, no aiohttp, no connection pools, no timeouts to configure, no auth headers.

---

## New File: `src/llm/bus_client.py` (~60 LOC)

Single source of truth for all LLM calls in voice_ai. Everything funnels through here.

```python
"""
bus_client.py — All LLM calls go through kc-bus → omniproxy.
No HTTP. No aiohttp. No SDK. Just pub/get.
"""
import os, sys, json
from uuid import uuid4
sys.path.insert(0, os.path.expanduser("~/kernclip/bus/sdk/python"))
from kernclip_bus import Bus

REQUEST  = "llm.omni.request"
RESPONSE = "llm.omni.response"

def _bus() -> Bus:
    return Bus()

def ask(prompt: str, model: str = "auto", system: str = None,
        history: list = None, timeout: int = 60) -> str:
    """Synchronous LLM call. Blocks until response."""
    bus = _bus()
    reply = f"{RESPONSE}.{uuid4().hex[:8]}"
    payload = {"prompt": prompt, "model": model, "reply_to": reply}
    if system:
        payload["system"] = system
    if history:
        payload["history"] = history
    bus.pub(REQUEST, json.dumps(payload))
    msg = bus.get(reply)  # blocks
    return json.loads(msg.data).get("text", "") if msg else ""

async def ask_async(prompt: str, **kw) -> str:
    """Async wrapper — runs ask() in executor so it doesn't block the event loop."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: ask(prompt, **kw))
```

---

## Migration of Each File

### `src/llm/voice_ai.py` (345 LOC → ~40 LOC)

Delete `VoiceAIService`, `Client`, `AsyncClient`, all session management.
Replace with thin functions that call `bus_client.ask/ask_async`:

```python
from .bus_client import ask_async

async def process_voice_prompt(user_input, conversation_history=None,
                                target_language="en", mode="voice_ai",
                                verbosity="balanced", use_tools=True) -> str:
    system = VOICE_AI_SYSTEM_PROMPT
    if verbosity == "concise":
        system += "\n- Keep responses very short"
    history = (conversation_history or [])[-5:]
    return await ask_async(user_input, system=system, history=history)
```

### `src/llm/translator.py` (~100 LOC → ~20 LOC)

Replace Groq HTTP client with `bus_client.ask_async`.

### `src/llm_manager.py` (108 LOC → ~30 LOC)

`process_dictation()` currently calls Groq. Replace with `bus_client.ask`.

### `src/http_client.py` (113 LOC → deleted)

Entire file gone. Nothing imports it after migration.

### `src/services/voice_ai_service.py` (360 LOC → deleted)

Appears to be a duplicate/older version of voice_ai.py. Confirm nothing imports it, delete.

---

## What `omni serve` must be running

Voice_ai becomes a pure bus consumer. It expects:
- `kc-bus` daemon running
- `omni serve` running (bus-native mode)

Both are already running as part of your normal environment. Voice_ai needs zero additional infrastructure.

---

## Implementation Order

1. Create `src/llm/bus_client.py`
2. Rewrite `src/llm/voice_ai.py` → thin wrappers over bus_client
3. Rewrite `src/llm/translator.py` → bus_client
4. Rewrite `src/llm_manager.py` → bus_client
5. Delete `src/http_client.py`
6. Confirm `src/services/voice_ai_service.py` is orphaned, delete
7. Test: `./run_voice_ai.sh` — app starts, voice round-trip works

---

## Definition of Done

```python
# This is the entire LLM integration for voice_ai after refactor:
from src.llm.bus_client import ask_async
response = await ask_async("Hello, how are you?")
# → "I'm doing well, thanks for asking!"
# No HTTP. No ports. No auth. No session lifecycle.
```
