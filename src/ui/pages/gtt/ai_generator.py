"""
AI Command Generator Worker.
Handles async command generation using OmniProxy SDK.
"""

import json
import asyncio
from PySide6.QtCore import Signal, QThread


class CommandGeneratorWorker(QThread):
    """Worker thread for AI command generation."""

    result_signal = Signal(str)

    def __init__(self, description: str, model_id: str, omniproxy_url: str):
        super().__init__()
        self.description = description
        self.model_id = model_id
        self.omniproxy_url = omniproxy_url

    def run(self) -> None:
        """Execute generation in background."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self._generate())
            self.result_signal.emit(result)
        finally:
            loop.close()

    async def _generate(self) -> str:
        """Generate command using OmniProxy SDK."""
        try:
            import sys
            sys.path.insert(0, "/home/craig/new-projects/omniproxy/sdk/python")
            from omniproxy import OmniProxy, Message

            system_prompt = """You are a GTT command generator. Convert natural language to GTT commands.
GTT Commands: focus, close, maximize, minimize, move-window, resize-window, launch, type, key,
cb, cb-set, cb-paste, sc, ocr, ocr-file, snap, hotkey-script, hotkey-input, macro-add, etc.
Output commands only, be concise."""

            client = OmniProxy(base_url=self.omniproxy_url)
            async with client:
                response = await client.chat.completions.create(
                    model=self.model_id,
                    messages=[Message(role="system", content=system_prompt),
                              Message(role="user", content=self.description)],
                    temperature=0.7, max_tokens=2048, timeout=30
                )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"


class CommandResultHandler:
    """Handles AI command generation results."""

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
        self.retry_count = 0

    def handle_result(self, result: str, on_retry, on_success, on_error) -> None:
        """Process generation result."""
        if result.startswith("RETRY:"):
            self._handle_retry(result, on_retry, on_error)
        elif result.startswith("Error:"):
            on_error(result)
        else:
            self._validate_and_success(result, on_success, on_error)

    def _handle_retry(self, result: str, on_retry, on_error) -> None:
        """Handle retry scenario."""
        self.retry_count += 1
        if self.retry_count <= self.max_retries:
            on_retry(self.retry_count)
        else:
            on_error(result.replace("RETRY:", ""))

    def _validate_and_success(self, result: str, on_success, on_error) -> None:
        """Validate result and call success handler."""
        try:
            commands = json.loads(result)
            if isinstance(commands, list):
                on_success(result, commands)
            else:
                on_error("Output is not a command list")
        except json.JSONDecodeError:
            on_error("Output is not valid JSON")

    def reset(self) -> None:
        """Reset retry counter."""
        self.retry_count = 0
