"""
Dynamic Model Registry for Voice AI
Single source of truth for all model information
Used by: TTS Server, ASR Server, GUI Components, Voice Cloning

Adding a new model = update ONE file
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ModelInfo:
    """Complete model metadata"""

    id: str  # Internal ID (e.g., "vibevoice")
    name: str  # Display name (e.g., "VibeVoice")
    display_name: str  # Full display name (e.g., "VibeVoice (Streaming)")
    type: str  # "tts" or "asr"

    # Language support
    languages: List[str] = field(default_factory=list)  # ["en", "es", "zh"]
    is_multilingual: bool = False
    language_options: Dict[str, str] = field(
        default_factory=dict
    )  # {"en": "English", "es": "Spanish"}

    # Voice cloning support
    voice_cloning_type: Optional[str] = None
    voice_cloning_languages: List[str] = field(default_factory=list)
    reference_phrases: Dict[str, str] = field(default_factory=dict)

    # Streaming support
    streaming: bool = False

    # Performance
    latency: Optional[str] = None  # "~300ms", "fast", "slow"

    # Model-specific settings
    voice_options: List[str] = field(default_factory=list)
    default_voice: Optional[str] = None
    default_settings: Dict[str, Any] = field(default_factory=dict)

    # UI hints
    description: Optional[str] = None
    instructions: Optional[str] = None  # Usage notes (e.g., voice cloning instructions)
    icon: Optional[str] = None


class ModelRegistry:
    """
    Single source of truth for all TTS/ASR models.

    Usage:
        # Get all TTS models for dropdown
        for model in ModelRegistry.get_tts_models():
            combo.addItem(model.display_name, model.id)

        # Get only voice cloning models
        for model in ModelRegistry.get_voice_cloning_models():
            combo.addItem(model.display_name, model.id)

        # Get model config
        model = ModelRegistry.get_model("vibevoice")
        if model.voice_cloning_type == "presets":
            # show preset selection
    """

    # =========================================================================
    # TTS MODELS - Single source of truth
    # =========================================================================
    TTS_MODELS: Dict[str, ModelInfo] = {
        "vibevoice": ModelInfo(
            id="vibevoice",
            name="VibeVoice",
            display_name="VibeVoice (Streaming)",
            type="tts",
            languages=["en", "es", "fr", "de", "it", "pt", "ja", "ko", "zh"],
            is_multilingual=True,
            voice_cloning_type="presets",  # Uses .pt preset files
            voice_cloning_languages=[
                "en",
                "es",
                "fr",
                "de",
                "it",
                "pt",
                "ja",
                "ko",
                "zh",
            ],
            reference_phrases={
                "en": "The quick brown fox jumps over the lazy dog. In the garden, beautiful flowers bloom under the golden sunlight.",
                "es": "El veloz murciélago hindú comía feliz cardillo y kiwi. La cigüeña tocaba el saxofón detrás del palenque de paja.",
                "fr": "Le renard brun rapide saute par-dessus le chien paresseux. Dans le jardin, de belles fleurs s'épanouissent sous le soleil doré.",
                "de": "Der schnelle braune Fuchs springt über den faulen Hund. Im Garten blühen schöne Blumen unter dem goldenen Sonnenlicht.",
                "it": "La rapida volpe marrone salta sopra il cane pigro. Nel giardino, belle fiori sbocciano sotto la luce dorata del sole.",
                "pt": "A rápida raposa marrom salta sobre o cão preguiçoso. No jardim, belas flores desabrocham sob a luz dourada do sol.",
                "ja": "素早い茶色の狐は怠け者の犬を飛び越えます。庭では、美しい花が金色の日光の下で咲いています。",
                "ko": "빠른 갈색 여우가 게으른 개를 뛰어넘습니다. 정원에서는 아름다운 꽃들이 황금빛 햇살 아래에서 피어납니다.",
                "zh": "敏捷的棕色狐狸跳过懒惰的狗。在花园里，美丽的花朵在金色的阳光下绽放。",
            },
            streaming=True,
            latency="~300ms",
            voice_options=["Carter", "Emma", "Fable", "Onyx", "Nova", "Shimmer"],
            default_voice="Carter",
            default_settings={
                "voice": "Carter",
                "language": "en",
                "temperature": 0.9,
                "top_p": 0.9,
                "cfg_scale": 1.5,
                "do_sample": False,
                "streaming": True,
            },
            description="Ultra-low latency streaming TTS with voice presets",
            instructions="Voice cloning: Import .pt preset files in Voice Cloning tab. Supports Carter, Emma, Fable, Onyx, Nova, Shimmer voices. Record reference audio in any of 9 languages.",
        ),
        "kanitts": ModelInfo(
            id="kanitts",
            name="KaniTTS",
            display_name="KaniTTS (English)",
            type="tts",
            languages=["en"],
            is_multilingual=False,
            voice_cloning_type=None,
            streaming=False,
            latency="fast",
            default_settings={
                "speed": 1.0,
                "temperature": 0.6,
            },
            description="High-quality English-only TTS model",
        ),
        "chatterbox-fp16": ModelInfo(
            id="chatterbox-fp16",
            name="Chatterbox FP16",
            display_name="Chatterbox FP16 (Voice Cloning)",
            type="tts",
            languages=["en"],
            is_multilingual=False,
            voice_cloning_type="reference",  # Uses WAV/MP3 reference audio
            voice_cloning_languages=["en"],
            reference_phrases={
                "en": "The quick brown fox jumps over the lazy dog. In the garden, beautiful flowers bloom under the golden sunlight."
            },
            streaming=False,
            latency="medium",
            default_settings={
                "cfg_weight": 0.1,
                "temperature": 0.8,
            },
            description="Voice cloning with reference audio (WAV/MP3)",
            instructions="Voice cloning: Provide a reference WAV/MP3 audio file. The model will clone the voice from the reference audio. Record reference audio for best results.",
        ),
        "qwen-tts": ModelInfo(
            id="qwen-tts",
            name="Qwen-TTS",
            display_name="Qwen-TTS",
            type="tts",
            languages=["zh", "en", "ja", "ko"],
            is_multilingual=True,
            voice_cloning_type=None,
            streaming=False,
            latency="medium",
            voice_options=["Vivian", "Alex", "Emma", "Liam", "Olivia"],
            default_voice="Vivian",
            default_settings={
                "speaker": "Vivian",
                "language": "Chinese",
                "instruction": None,
                "non_streaming_mode": True,
            },
            description="Multi-language TTS from Qwen",
        ),
        "sopranotts": ModelInfo(
            id="sopranotts",
            name="SopranoTTS",
            display_name="SopranoTTS",
            type="tts",
            languages=["en"],
            is_multilingual=False,
            voice_cloning_type=None,
            streaming=False,
            latency="medium",
            default_settings={
                "temperature": 0.3,
                "top_p": 0.95,
                "repetition_penalty": 1.2,
            },
            description="High-quality English TTS",
        ),
        "kittentts": ModelInfo(
            id="kittentts",
            name="KittenTTS",
            display_name="KittenTTS",
            type="tts",
            languages=["en"],
            is_multilingual=False,
            voice_cloning_type=None,
            streaming=False,
            latency="fast",
            voice_options=["default"],
            default_voice="default",
            default_settings={
                "voice": "default",
                "speed": 1.0,
                "clean_text": True,
            },
            description="Fast English TTS for quick generation",
        ),
        "pockettts": ModelInfo(
            id="pockettts",
            name="PocketTTS",
            display_name="PocketTTS",
            type="tts",
            languages=["en"],
            is_multilingual=False,
            voice_cloning_type="reference_audio",
            voice_cloning_languages=["en"],
            reference_phrases={
                "en": "The quick brown fox jumps over the lazy dog.",
            },
            streaming=True,
            latency="medium",
            voice_options=["default"],
            default_voice="default",
            default_settings={
                "voice": "default",
                "max_frames": 500,
            },
            description="English-only TTS with voice cloning from audio reference",
        ),
    }

    # =========================================================================
    # ASR MODELS - Single source of truth
    # =========================================================================
    ASR_MODELS: Dict[str, ModelInfo] = {
        "canary-1b-v2": ModelInfo(
            id="canary-1b-v2",
            name="Canary 1B v2",
            display_name="Canary 1B v2",
            type="asr",
            languages=["en", "de", "es", "fr"],
            is_multilingual=True,
            default_settings={},
            description="High-accuracy multilingual ASR",
        ),
        "parakeet-tdt-v3": ModelInfo(
            id="parakeet-tdt-v3",
            name="Parakeet TDT v3",
            display_name="Parakeet TDT v3",
            type="asr",
            languages=["en"],
            is_multilingual=False,
            default_settings={},
            description="Fast English ASR model",
        ),
        "sensevoice-small": ModelInfo(
            id="sensevoice-small",
            name="SenseVoice Small",
            display_name="SenseVoice Small",
            type="asr",
            languages=["en", "zh", "yue", "ja", "ko"],
            is_multilingual=True,
            default_settings={},
            description="Efficient multilingual ASR",
        ),
        "qwen3-asr": ModelInfo(
            id="qwen3-asr",
            name="Qwen3-0.6b",
            display_name="Qwen3-0.6b (52 langs)",
            type="asr",
            languages=[
                "en",
                "zh",
                "de",
                "fr",
                "es",
                "it",
                "ja",
                "ko",
                "ar",
                "ru",
                "pt",
                "nl",
                "pl",
                "tr",
                "vi",
                "th",
                "id",
                "ms",
                "hi",
                "bn",
                "ur",
                "fa",
                "ar",
                "he",
                "el",
                "hu",
                "cs",
                "sk",
                "uk",
                "bg",
                "ro",
                "ca",
                "fi",
                "da",
                "sv",
                "no",
                "et",
                "lv",
                "lt",
                "sl",
                "hr",
                "be",
                "mk",
                "sq",
                "bs",
                "sr",
                "ml",
                "ta",
                "te",
                "kn",
                "gu",
                "mr",
                "pa",
                "ne",
                "si",
                "am",
                "ka",
                "kk",
                "uz",
                "tg",
                "mn",
                "my",
                "lo",
                "km",
                "ceb",
                "jw",
                "su",
                "ny",
                "sn",
                "rw",
                "st",
                "af",
            ],
            is_multilingual=True,
            default_settings={},
            description="Qwen3 0.6B parameter ASR model with 52 language support",
        ),
    }

    # =========================================================================
    # CLASS METHODS - For GUI and API usage
    # =========================================================================

    @classmethod
    def get_tts_models(
        cls,
        filter_language: Optional[str] = None,
        filter_voice_cloning: Optional[str] = None,
        filter_streaming: Optional[bool] = None,
    ) -> List["ModelInfo"]:
        """
        Get TTS models with optional filters.

        Args:
            filter_language: Filter by language (e.g., "en")
            filter_voice_cloning: "presets" or "reference" to filter by cloning type
            filter_streaming: True/False to filter by streaming support

        Returns:
            List of ModelInfo objects
        """
        models = list(cls.TTS_MODELS.values())

        if filter_language:
            models = [m for m in models if filter_language in m.languages]

        if filter_voice_cloning:
            models = [m for m in models if m.voice_cloning_type == filter_voice_cloning]

        if filter_streaming is not None:
            models = [m for m in models if m.streaming == filter_streaming]

        return models

    @classmethod
    def get_asr_models(cls, filter_language: Optional[str] = None) -> List["ModelInfo"]:
        """Get ASR models with optional language filter."""
        models = list(cls.ASR_MODELS.values())

        if filter_language:
            models = [m for m in models if filter_language in m.languages]

        return models

    @classmethod
    def get_voice_cloning_models(cls) -> List[ModelInfo]:
        """Get all models that support voice cloning."""
        return [m for m in cls.TTS_MODELS.values() if m.voice_cloning_type is not None]

    @classmethod
    def get_streaming_models(cls) -> List[ModelInfo]:
        """Get all streaming TTS models."""
        return [m for m in cls.TTS_MODELS.values() if m.streaming]

    @classmethod
    def get_model(cls, model_id: str) -> Optional[ModelInfo]:
        """Get a specific model by ID (checks both TTS and ASR)."""
        return cls.TTS_MODELS.get(model_id) or cls.ASR_MODELS.get(model_id)

    @classmethod
    def get_model_ids(cls, model_type: str = "tts") -> List[str]:
        """Get all model IDs for a given type."""
        if model_type == "tts":
            return list(cls.TTS_MODELS.keys())
        return list(cls.ASR_MODELS.keys())

    @classmethod
    def get_display_names(cls, model_type: str = "tts") -> List[Tuple[str, str]]:
        """Get all display names for a given type. Returns list of (id, display_name) tuples."""
        if model_type == "tts":
            return [(m.id, m.display_name) for m in cls.TTS_MODELS.values()]
        return [(m.id, m.display_name) for m in cls.ASR_MODELS.values()]

    @classmethod
    def get_default_settings(cls, model_id: str) -> Dict[str, Any]:
        """Get default settings for a model."""
        model = cls.get_model(model_id)
        if model:
            return dict(model.default_settings)
        return {}

    @classmethod
    def get_voice_options(cls, model_id: str) -> List[str]:
        """Get voice options for a model."""
        model = cls.get_model(model_id)
        if model:
            return list(model.voice_options)
        return []

    @classmethod
    def supports_voice_cloning(cls, model_id: str) -> bool:
        """Check if a model supports voice cloning."""
        model = cls.get_model(model_id)
        return model.voice_cloning_type is not None if model else False

    @classmethod
    def get_voice_cloning_type(cls, model_id: str) -> Optional[str]:
        """Get the voice cloning type for a model (presets/reference/None)."""
        model = cls.get_model(model_id)
        return model.voice_cloning_type if model else None

    @classmethod
    def get_asr_languages(cls) -> Dict[str, str]:
        """Get all available ASR languages (code -> name mapping)."""
        return {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic",
            "hi": "Hindi",
        }

    @classmethod
    def get_tts_languages(cls, model_id: str) -> Dict[str, str]:
        """Get language options for a specific TTS model."""
        model = cls.get_model(model_id)
        if not model:
            return {"en": "English"}

        if hasattr(model, "language_options") and model.language_options:
            return model.language_options

        lang_names = {
            "en": "English",
            "zh": "Chinese",
            "es": "Spanish",
            "ja": "Japanese",
            "ko": "Korean",
            "fr": "French",
            "de": "German",
            "ar": "Arabic",
            "pt": "Portuguese",
            "ru": "Russian",
            "hi": "Hindi",
            "it": "Italian",
        }
        return {code: lang_names.get(code, code.upper()) for code in model.languages}


# =========================================================================
# BACKWARD COMPATIBILITY - Keep existing API working
# =========================================================================

# Old-style lists for backward compatibility
TTS_MODELS_LIST = [
    {
        "id": m.id,
        "name": m.name,
        "type": "tts",
        "streaming": m.streaming,
        "voice_cloning": m.voice_cloning_type is not None,
        "languages": m.languages,
    }
    for m in ModelRegistry.TTS_MODELS.values()
]

ASR_MODELS_LIST = [
    {"id": m.id, "name": m.name, "type": "asr"}
    for m in ModelRegistry.ASR_MODELS.values()
]


# Global instance (for old code)
model_registry = ModelRegistry()
