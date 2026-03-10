"""
Voice Cloning Module.

A modular voice cloning interface for PySide6 applications.
Supports VibeVoice (voice presets) and Chatterbox FP16 (reference audio).

Module Structure:
    - voice_cloning_page.py: Main coordinator widget
    - widgets.py: Reusable UI sub-components
    - handlers.py: Signal/slot business logic
    - services.py: Qt-agnostic business logic
    - worker.py: Background thread workers
    - models.py: Data models and enums

Usage:
    from ui.pages.voice_cloning import VoiceCloningPage

    page = VoiceCloningPage(main_window)
    layout.addWidget(page)

Signal Contracts:
    # ModelSelectionCard -> VoiceCloningPage
    model_changed = Signal(str)  # emits: model_id ("vibevoice" | "chatterbox-fp16")

    # VibeVoiceSelectionCard -> VoiceCloningPage
    voice_selected = Signal(str)   # emits: voice_name
    import_requested = Signal()
    delete_requested = Signal()
    refresh_requested = Signal()

    # ChatterboxReferenceCard -> VoiceCloningPage
    browse_requested = Signal()

    # GenerationControlsCard -> VoiceCloningPage
    generate_requested = Signal()
    play_requested = Signal()
    save_requested = Signal()

    # VoiceCloneWorker -> VoiceCloningPage
    finished = Signal(object)  # emits: audio_data (list[float])
    error = Signal(str)        # emits: error_message
    progress = Signal(str)     # emits: status_message
"""

from .models import (
    TTSModel,
    Language,
    VoicePreset,
    GenerationRequest,
    GenerationResult,
    VoiceCloningState,
)

from .widgets import (
    ModelSelectionCard,
    VibeVoiceSelectionCard,
    ChatterboxReferenceCard,
    TextInputCard,
    GenerationControlsCard,
)

from .handlers import (
    VoiceManagementHandler,
    ReferenceAudioHandler,
    GenerationHandler,
)

from .services import (
    AudioService,
    VoiceCloningStateService,
)

from .worker import VoiceCloneWorker

from .voice_cloning_page import VoiceCloningPage

__all__ = [
    # Main page
    "VoiceCloningPage",
    # Models
    "TTSModel",
    "Language",
    "VoicePreset",
    "GenerationRequest",
    "GenerationResult",
    "VoiceCloningState",
    # Widgets
    "ModelSelectionCard",
    "VibeVoiceSelectionCard",
    "ChatterboxReferenceCard",
    "TextInputCard",
    "GenerationControlsCard",
    # Handlers
    "VoiceManagementHandler",
    "ReferenceAudioHandler",
    "GenerationHandler",
    # Services
    "AudioService",
    "VoiceCloningStateService",
    # Worker
    "VoiceCloneWorker",
]
