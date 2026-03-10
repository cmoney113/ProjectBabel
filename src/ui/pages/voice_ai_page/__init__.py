"""
Voice AI Page Package

Modular architecture for the Voice AI page:
- voice_ai_page: Main coordinator widget
- widgets: Sub-widgets (recording, models, transcription, response, mode)
- handlers: Signal handlers (model, recording, UI)
- services: Business logic (text processing, TTS)
- state: State management
"""

from .voice_ai_page import VoiceAIPage

__all__ = ["VoiceAIPage"]
