"""
Voice Cloning Page - Backward Compatibility Module.

This module re-exports VoiceCloningPage from the new modular package
for backward compatibility with existing imports.

New code should import from:
    from ui.pages.voice_cloning import VoiceCloningPage

Legacy code can continue using:
    from ui.pages.voice_cloning_page import VoiceCloningPage
"""

# Re-export from new modular package for backward compatibility
from .voice_cloning import (
    VoiceCloningPage,
    TTSModel,
    Language,
    VoicePreset,
    GenerationRequest,
    GenerationResult,
    VoiceCloningState,
    ModelSelectionCard,
    VibeVoiceSelectionCard,
    ChatterboxReferenceCard,
    TextInputCard,
    GenerationControlsCard,
    VoiceManagementHandler,
    ReferenceAudioHandler,
    GenerationHandler,
    AudioService,
    VoiceCloningStateService,
    VoiceCloneWorker,
)

__all__ = [
    "VoiceCloningPage",
    "TTSModel",
    "Language",
    "VoicePreset",
    "GenerationRequest",
    "GenerationResult",
    "VoiceCloningState",
    "ModelSelectionCard",
    "VibeVoiceSelectionCard",
    "ChatterboxReferenceCard",
    "TextInputCard",
    "GenerationControlsCard",
    "VoiceManagementHandler",
    "ReferenceAudioHandler",
    "GenerationHandler",
    "AudioService",
    "VoiceCloningStateService",
    "VoiceCloneWorker",
]
