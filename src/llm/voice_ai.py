"""
Voice AI Service using OmniProxy SDK
====================================
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

# Import OmniProxy SDK
sys.path.insert(0, str(os.path.expanduser("~/omniproxy/sdk/python")))
from omniproxy import Client, AsyncClient, Message

logger = logging.getLogger(__name__)


# System prompts for different modes
VOICE_AI_SYSTEM_PROMPT = """You are a helpful AI voice assistant. Respond conversationally and concisely.

Guidelines:
- Keep responses natural and conversational
- Be helpful and accurate
- If you don't know something, say so honestly
- Respond in the target language if specified
- You have access to tools for file operations, web search, and more - use them when helpful"""

VOICE_AI_TOOLS_SYSTEM_PROMPT = """You are a helpful AI voice assistant with tool capabilities.

You have access to TermPipe tools for:
- File operations (read, write, search, list)
- Web search
- Shell commands
- And more

Guidelines:
- Use tools when they would help answer the user's request
- Keep responses natural and conversational
- Be helpful and accurate
- Respond in the target language if specified"""

DICTATION_SYSTEM_PROMPT = """You are a text post-processing assistant. Clean up and correct transcribed speech.

Rules:
- Fix obvious transcription errors
- Add proper punctuation
- Capitalize first letters of sentences
- Do NOT add any commentary, explanations, or additional content
- Only output the corrected text"""


class VoiceAIService:
    """OmniProxy-based voice AI service"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "qwen3-max",
    ):
        self.api_key = api_key
        self.base_url = base_url or "http://127.0.0.1:8743"
        self.model = model

        # Initialize OmniProxy sync client for convenience methods
        self._sync_client = Client(base_url=self.base_url, api_key=api_key)

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

    async def _call_omniproxy_with_tools(
        self, messages: List[Dict], temperature: float = 0.3, max_tokens: int = 500
    ) -> Dict[str, Any]:
        """Call OmniProxy with TermPipe tools enabled (agentic loop)"""
        try:
            async with AsyncClient(base_url=self.base_url, api_key=self.api_key) as client:
                # Use run_with_tools for agentic loop with automatic tool execution
                content = await client.chat.completions.run_with_tools(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    use_termpipe=True,  # Auto-wire all TermPipe tools
                    max_turns=5,  # Limit tool call iterations
                )
                return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "content": "", "error": str(e)}

    async def _call_omniproxy(
        self, messages: List[Dict], temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Call OmniProxy gateway via SDK (no API key needed for local gateway)"""
        try:
            async with AsyncClient(base_url=self.base_url, api_key=self.api_key) as client:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=500,
                )
                content = response.choices[0].message.get("content", "")
                return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "content": "", "error": str(e)}

    async def process(
        self,
        user_input: str,
        conversation_history: List[Dict] = None,
        target_language: str = "en",
        mode: str = "voice_ai",  # "voice_ai" or "dictation"
        verbosity: str = "balanced",  # "concise", "balanced", "detailed"
        use_tools: bool = True,  # Enable TermPipe tools in voice_ai mode
    ) -> str:
        """
        Process user input through voice AI.

        Args:
            user_input: The transcribed text from ASR
            conversation_history: Previous messages [{"role": "user/assistant", "content": "..."}]
            target_language: Language code (e.g., "en", "zh")
            mode: "voice_ai" for conversation, "dictation" for clean output
            verbosity: "concise", "balanced", "detailed"
            use_tools: Enable TermPipe tools (file ops, web search, etc.) in voice_ai mode

        Returns:
            Processed text response
        """
        conversation_history = conversation_history or []

        # Build messages
        if mode == "dictation":
            system_prompt = DICTATION_SYSTEM_PROMPT
            temperature = 0.1
            use_tools = False  # Never use tools in dictation mode
        else:
            # Use tools-aware prompt if tools enabled
            if use_tools:
                system_prompt = VOICE_AI_TOOLS_SYSTEM_PROMPT
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

        # Call OmniProxy - use tools-enabled path if requested
        if use_tools:
            result = await self._call_omniproxy_with_tools(messages, temperature=temperature)
        else:
            result = await self._call_omniproxy(messages, temperature=temperature)

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
                result = await self._call_omniproxy(messages, temperature=temperature)

                if result["success"]:
                    return result["content"]
                else:
                    logger.error(
                        f"Voice AI error after sanitization: {result.get('error')}"
                    )

            return f"[AI Error: {error_msg}]"

    def process_sync(
        self,
        user_input: str,
        conversation_history: List[Dict] = None,
        target_language: str = "en",
        mode: str = "voice_ai",
        verbosity: str = "balanced",
    ) -> str:
        """
        Synchronous version for non-async contexts.

        Uses the sync OmniProxy client.
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

        try:
            # Use sync client
            completion = self._sync_client.completions_create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=500,
            )
            content = completion.choices[0].message.get("content", "")
            return content
        except Exception as e:
            logger.error(f"Voice AI sync error: {e}")
            return f"[AI Error: {e}]"


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
    use_tools: bool = True,
) -> str:
    """Quick voice prompt processing
    
    Args:
        user_input: The transcribed text
        conversation_history: Previous messages
        target_language: Language code
        mode: "voice_ai" or "dictation"
        verbosity: "concise", "balanced", "detailed"
        use_tools: Enable TermPipe tools (file ops, web search, etc.)
    """
    service = get_voice_ai()
    return await service.process(
        user_input=user_input,
        conversation_history=conversation_history,
        target_language=target_language,
        mode=mode,
        verbosity=verbosity,
        use_tools=use_tools,
    )


def process_voice_prompt_sync(
    user_input: str,
    conversation_history: List[Dict] = None,
    target_language: str = "en",
    mode: str = "voice_ai",
    verbosity: str = "balanced",
) -> str:
    """Synchronous voice prompt processing for non-async contexts"""
    service = get_voice_ai()
    return service.process_sync(
        user_input=user_input,
        conversation_history=conversation_history,
        target_language=target_language,
        mode=mode,
        verbosity=verbosity,
    )