"""
Dynamic Model Registry for Voice AI
Automatically discovers and registers available ASR and TTS models
Source of truth: servers/tts_server.py and servers/asr_server.py
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# TTS Models from tts_server.py
TTS_MODELS = [
    {"id": "chatterbox-fp16", "name": "Chatterbox FP16", "type": "tts"},
    {"id": "sopranotts", "name": "SopranoTTS", "type": "tts"},
    {"id": "qwen-tts", "name": "Qwen-TTS", "type": "tts"},
    {"id": "kittentts", "name": "KittenTTS", "type": "tts"},
    {"id": "vibevoice", "name": "VibeVoice Realtime", "type": "tts", "streaming": True, "voice_cloning": True, "languages": ["en", "es", "fr", "de", "it", "pt", "ja", "ko", "zh"]},
]

# ASR Models from asr_server.py
ASR_MODELS = [
    {"id": "canary-1b-v2", "name": "Canary 1B v2", "type": "asr"},
    {"id": "parakeet-tdt-v3", "name": "Parakeet TDT v3", "type": "asr"},
    {"id": "sensevoice-small", "name": "SenseVoice Small", "type": "asr"},
]


@dataclass
class ModelConfig:
    """Configuration for a model with its settings"""

    id: str
    name: str
    type: str  # 'tts' or 'asr'
    streaming: bool = False
    default_settings: Optional[Dict[str, Any]] = None
    voice_options: Optional[List[str]] = None
    language_options: Optional[List[str]] = None

    def __post_init__(self):
        if self.default_settings is None:
            self.default_settings = {}
        if self.voice_options is None:
            self.voice_options = []
        if self.language_options is None:
            self.language_options = []


class ModelRegistry:
    """Dynamic registry that manages available models and their configurations"""

    def __init__(self):
        self.models = {}
        self._initialize_models()

    def _initialize_models(self):
        """Initialize all available models with their configurations"""
        # TTS Models
        for model_info in TTS_MODELS:
            model_id = model_info["id"]
            config = ModelConfig(
                id=model_id,
                name=model_info["name"],
                type="tts",
                streaming=model_info.get("streaming", False),
            )

            # Add model-specific settings
            if model_id == "vibevoice":
                config.voice_options = [
                    "Carter",
                    "Emma",
                    "Fable",
                    "Onyx",
                    "Nova",
                    "Shimmer",
                ]
                config.language_options = [
                    "en",
                    "es",
                    "fr",
                    "de",
                    "it",
                    "pt",
                    "ja",
                    "ko",
                    "zh",
                ]
                config.default_settings = {
                    "voice": "Carter",
                    "language": "en",
                    "temperature": 0.9,
                    "top_p": 0.9,
                    "cfg_scale": 1.5,
                    "do_sample": False,
                    "streaming": True,
                }
            elif model_id == "kittentts":
                config.voice_options = ["default"]
                config.default_settings = {
                    "voice": "default",
                    "speed": 1.0,
                    "clean_text": True,
                }
            elif model_id == "qwen-tts":
                config.voice_options = ["Vivian", "Alex", "Emma", "Liam", "Olivia"]
                config.language_options = ["Chinese", "English", "Japanese", "Korean"]
                config.default_settings = {
                    "speaker": "Vivian",
                    "language": "Chinese",
                    "instruction": None,
                    "non_streaming_mode": True,
                }
            elif model_id == "sopranotts":
                config.default_settings = {
                    "temperature": 0.3,
                    "top_p": 0.95,
                    "repetition_penalty": 1.2,
                }
            elif model_id == "chatterbox-fp16":
                config.default_settings = {"cfg_weight": 0.1, "temperature": 0.8}

            self.models[model_id] = config

        # ASR Models
        for model_info in ASR_MODELS:
            model_id = model_info["id"]
            config = ModelConfig(id=model_id, name=model_info["name"], type="asr")
            self.models[model_id] = config

    def get_tts_models(self) -> List[ModelConfig]:
        """Get all available TTS models"""
        return [model for model in self.models.values() if model.type == "tts"]

    def get_asr_models(self) -> List[ModelConfig]:
        """Get all available ASR models"""
        return [model for model in self.models.values() if model.type == "asr"]

    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get a specific model by ID"""
        return self.models.get(model_id)

    def get_model_names(self, model_type: str = "tts") -> List[str]:
        """Get model names for dropdowns"""
        if model_type == "tts":
            return [model.name for model in self.get_tts_models()]
        return [model.name for model in self.get_asr_models()]

    def get_model_ids(self, model_type: str = "tts") -> List[str]:
        """Get model IDs for internal use"""
        if model_type == "tts":
            return [model.id for model in self.get_tts_models()]
        return [model.id for model in self.get_asr_models()]

    def get_default_settings(self, model_id: str) -> Dict[str, Any]:
        """Get default settings for a model"""
        model = self.get_model(model_id)
        if model and model.default_settings:
            return dict(model.default_settings)
        return {}

    def get_voice_options(self, model_id: str) -> List[str]:
        """Get voice options for a model"""
        model = self.get_model(model_id)
        if model and model.voice_options:
            return list(model.voice_options)
        return []

    def get_language_options(self, model_id: str) -> List[str]:
        """Get language options for a model"""
        model = self.get_model(model_id)
        if model and model.language_options:
            return list(model.language_options)
        return []


# Global registry instance
model_registry = ModelRegistry()
