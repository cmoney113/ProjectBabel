"""
LLM Module - Unified LLM interfaces
=====================================
This module provides:
- Translation service (Groq API)
- Voice AI service (OmniProxy SDK - Qwen3-Max, MiniMax-M2, etc.)

Both can be used independently or through the pipeline orchestrator.
"""

from .translator import TranslationService, translate_text
from .voice_ai import VoiceAIService, process_voice_prompt

__all__ = [
    "TranslationService",
    "translate_text",
    "VoiceAIService", 
    "process_voice_prompt",
]
