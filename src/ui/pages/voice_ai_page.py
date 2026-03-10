"""
Voice AI Page - Backward Compatibility Shim

This file re-exports VoiceAIPage from the new modular package location.
Update imports to use: from src.ui.pages.voice_ai_page import VoiceAIPage

Deprecated: This shim will be removed in a future version.
"""

from .voice_ai_page.voice_ai_page import VoiceAIPage

__all__ = ["VoiceAIPage"]
