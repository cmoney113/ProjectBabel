"""
Voice AI Service using iFlow Qwen3-Max
======================================
For conversational AI processing in the voice pipeline.

Usage:
    from src.llm import VoiceAIService, process_voice_prompt

    # Voice AI mode (with conversation history)
    result = await process_voice_prompt(
        user_input="Hello, how are you?",
        conversation_history=[{"role": "user", "content": "Hi"}],
        target_language="en"
    )

    # Dictation mode (clean transcript)
    result = await process_voice_prompt(
        user_input="The quick brown fox",
        conversation_history=[],
        target_language="en",
        mode="dictation"
    )
"""

import os
import sys
import logging
from typing import Optional, List, Dict, Any
import asyncio
import aiohttp
from src.http_client import get_http_client

logger = logging.getLogger(__name__)

# Try to import iFlow, fall back to direct API
try:
    sys.path.insert(0, str(os.path.expanduser("~/Unified_Free_Models/iflow_api")))
    from iflow_api import IFlowAPI

    HAS_IFLOW = True
except ImportError:
    HAS_IFLOW = False


# System prompts for different modes
VOICE_AI_SYSTEM_PROMPT = """You are a helpful AI voice assistant. Respond conversationally and concisely.

Guidelines:
- Keep responses natural and conversational
- Be helpful and accurate
- If you don't know something, say so honestly
- Respond in the target language if specified"""

DICTATION_SYSTEM_PROMPT = """You are a text post-processing assistant. Clean up and correct transcribed speech.

Rules:
- Fix obvious transcription errors
- Add proper punctuation
- Capitalize first letters of sentences
- Do NOT add any commentary, explanations, or additional content
- Only output the corrected text"""


class VoiceAIService:
    """iFlow-based voice AI service"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or "https://apis.iflow.cn/v1"
        self.model = "kimi-k2"  # Less restrictive content filters than qwen3-max

        # Fallback to direct API if iFlow not available
        self._use_direct_api = not HAS_IFLOW

        # Profanity list for sanitization (only used when content filter triggers)
        self.profanity_list = [
            "fuck",
            "fucking",
            "fucked",
            "fucker",
            "shit",
            "damn",
            "goddamn",
            "bitch",
            "bastard",
            "asshole",
            "crap",
            "piss",
            "dick",
            "cock",
        ]

    def _sanitize_text(self, text: str) -> str:
        """Sanitize profanity from text - only called when content filter triggers"""
        sanitized = text
        for word in self.profanity_list:
            # Case-insensitive replacement
            sanitized = sanitized.replace(word, "[filtered]")
            sanitized = sanitized.replace(word.capitalize(), "[filtered]")
            sanitized = sanitized.replace(word.upper(), "[filtered]")
        return sanitized

    async def _call_iflow(
        self, messages: List[Dict], temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Call iFlow API directly"""
        if HAS_IFLOW:
            api = IFlowAPI()
            result = await api.chat(
                prompt=messages[-1]["content"],
                model=self.model,
                system_prompt=messages[0]["content"]
                if messages and messages[0]["role"] == "system"
                else None,
                temperature=temperature,
            )
            return {
                "success": result.success,
                "content": result.content,
                "error": result.error,
            }
        else:
            # Direct API call
            return await self._call_direct_api(messages, temperature)

    async def _call_direct_api(
        self, messages: List[Dict], temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Direct API call fallback"""
        if not self.api_key:
            # Try to load from ~/.iflow/settings.json
            import json
            from pathlib import Path

            settings_path = Path.home() / ".iflow" / "settings.json"
            if settings_path.exists():
                with open(settings_path) as f:
                    settings = json.load(f)
                self.api_key = settings.get("apiKey")

        if not self.api_key:
            return {"success": False, "content": "", "error": "No iFlow API key"}

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 500,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            http_client = get_http_client()
            session = await http_client.get_session()
            async with session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "success": True,
                        "content": data["choices"][0]["message"]["content"],
                    }
                else:
                    error = await resp.text()
                    return {"success": False, "content": "", "error": error}
        except Exception as e:
            return {"success": False, "content": "", "error": str(e)}

    async def process(
        self,
        user_input: str,
        conversation_history: List[Dict] = None,
        target_language: str = "en",
        mode: str = "voice_ai",  # "voice_ai" or "dictation"
        verbosity: str = "balanced",  # "concise", "balanced", "detailed"
    ) -> str:
        """
        Process user input through voice AI.

        Args:
            user_input: The transcribed text from ASR
            conversation_history: Previous messages [{"role": "user/assistant", "content": "..."}]
            target_language: Language code (e.g., "en", "zh")
            mode: "voice_ai" for conversation, "dictation" for clean output
            verbosity: "concise", "balanced", "detailed"

        Returns:
            Processed text response
        """
        conversation_history = conversation_history or []

        # Build messages
        if mode == "dictation":
            system_prompt = DICTATION_SYSTEM_PROMPT
            temperature = 0.1
        else:
            system_prompt = VOICE_AI_SYSTEM_PROMPT
            temperature = 0.3
            if verbosity == "concise":
                system_prompt += "\n- Keep responses very short and direct"
            elif verbosity == "detailed":
                system_prompt += "\n- Provide thorough, detailed responses"

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 5 messages max)
        for msg in conversation_history[-5:]:
            messages.append(msg)

        # Add current input
        messages.append({"role": "user", "content": user_input})

        # Call API
        result = await self._call_iflow(messages, temperature=temperature)

        if result["success"]:
            return result["content"]
        else:
            error_msg = result.get("error", "Unknown")
            logger.error(f"Voice AI error: {error_msg}")

            # Check for content filter errors - sanitize and retry
            if (
                "DataInspectionFailed" in error_msg
                or "inappropriate content" in error_msg
            ):
                logger.warning("Content filter triggered, sanitizing and retrying...")
                sanitized_input = self._sanitize_text(user_input)
                logger.info(f"Sanitized input: {sanitized_input}")

                # Replace user content with sanitized version
                messages[-1]["content"] = sanitized_input

                # Retry with sanitized text
                result = await self._call_iflow(messages, temperature=temperature)

                if result["success"]:
                    return result["content"]
                else:
                    logger.error(
                        f"Voice AI error after sanitization: {result.get('error')}"
                    )

            return f"[AI Error: {error_msg}]"


# Singleton
_voice_ai: Optional[VoiceAIService] = None


def get_voice_ai() -> VoiceAIService:
    """Get singleton voice AI service"""
    global _voice_ai
    if _voice_ai is None:
        _voice_ai = VoiceAIService()
    return _voice_ai


async def process_voice_prompt(
    user_input: str,
    conversation_history: List[Dict] = None,
    target_language: str = "en",
    mode: str = "voice_ai",
    verbosity: str = "balanced",
) -> str:
    """Quick voice prompt processing"""
    service = get_voice_ai()
    return await service.process(
        user_input=user_input,
        conversation_history=conversation_history,
        target_language=target_language,
        mode=mode,
        verbosity=verbosity,
    )
