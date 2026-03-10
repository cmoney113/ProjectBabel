"""
Data models and enums for Voice Cloning module.

This module contains all data structures used across the voice cloning feature.
Kept separate from UI logic for better testability and reusability.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional

# Import from ModelRegistry as single source of truth
from src.model_registry import ModelRegistry


class TTSModel(Enum):
    """Supported TTS models for voice cloning - populated from ModelRegistry."""

    VIBEVOICE = "vibevoice"
    CHATTERBOX_FP16 = "chatterbox-fp16"
    KANITTS = "kanitts"

    @classmethod
    def get_all_with_cloning(cls) -> list["TTSModel"]:
        """Return all models that support voice cloning."""
        return [
            model for model in cls if ModelRegistry.supports_voice_cloning(model.value)
        ]

    @classmethod
    def get_display_name(cls, model_id: str) -> str:
        """Get display name from ModelRegistry."""
        model = ModelRegistry.get_model(model_id)
        return model.display_name if model else model_id


class Language(Enum):
    """Supported languages for TTS synthesis - populated from ModelRegistry."""

    ENGLISH = ("en", "English")
    SPANISH = ("es", "Spanish")
    FRENCH = ("fr", "French")
    GERMAN = ("de", "German")
    ITALIAN = ("it", "Italian")
    PORTUGUESE = ("pt", "Portuguese")
    CHINESE = ("zh", "Chinese")
    JAPANESE = ("ja", "Japanese")
    KOREAN = ("ko", "Korean")

    def __init__(self, code: str, display_name: str):
        self.code = code
        self.display_name = display_name

    @classmethod
    def get_by_code(cls, code: str) -> "Language":
        """Get language enum by code."""
        for lang in cls:
            if lang.code == code:
                return lang
        return cls.ENGLISH

    @classmethod
    def get_all_codes(cls) -> list[str]:
        """Get all language codes."""
        return [lang.code for lang in cls]

    @classmethod
    def get_all_display_names(cls) -> list[str]:
        """Get all language display names."""
        return [lang.display_name for lang in cls]


@dataclass
class VoicePreset:
    """Represents a VibeVoice voice preset."""

    name: str
    file_path: Path
    is_protected: bool = False

    @property
    def display_name(self) -> str:
        """Get display name for UI."""
        return self.name


@dataclass
class GenerationRequest:
    """Request parameters for voice generation."""

    text: str
    model: TTSModel
    voice_name: Optional[str] = None
    reference_audio_path: Optional[Path] = None
    language_code: str = "en"


@dataclass
class GenerationResult:
    """Result from voice generation."""

    success: bool
    audio_data: Optional[list[float]] = None
    sample_rate: int = 24000
    error_message: Optional[str] = None
    status_message: str = ""


@dataclass
class VoiceCloningState:
    """Centralized state for voice cloning page."""

    # Current selections
    selected_model: TTSModel = TTSModel.VIBEVOICE
    selected_voice: Optional[str] = None
    reference_audio_path: Optional[str] = None
    selected_language: str = "en"
    input_text: str = ""

    # Generation state
    is_generating: bool = False
    generated_audio: Optional[list[float]] = None
    status_message: str = ""

    # Available voices
    available_voices: list[str] = field(default_factory=list)

    def reset_generation_state(self):
        """Reset generation-related state."""
        self.is_generating = False
        self.generated_audio = None
        self.status_message = ""
