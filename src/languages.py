# Language configurations for voice AI pipeline

# Canary ASR - all 25 supported languages
CANARY_LANGUAGES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "ru": "Russian", "zh": "Chinese",
    "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "hi": "Hindi",
    "tr": "Turkish", "pl": "Polish", "nl": "Dutch", "sv": "Swedish",
    "da": "Danish", "no": "Norwegian", "fi": "Finnish", "el": "Greek",
    "he": "Hebrew", "th": "Thai", "vi": "Vietnamese", "id": "Indonesian"
}

# TTS Models and their supported languages
TTS_MODELS = {
    "qwen-tts": {
        "name": "Qwen3-TTS",
        "languages": {
            "en": "English", "es": "Spanish", "fr": "French", "de": "German",
            "it": "Italian", "pt": "Portuguese", "ru": "Russian", 
            "zh": "Chinese", "ja": "Japanese", "ko": "Korean"
        }
    },
    "chatterbox-fp16": {
        "name": "Chatterbox FP16",
        "languages": {
            "ar": "Arabic", "de": "German", "el": "Greek", "en": "English",
            "es": "Spanish", "fi": "Finnish", "fr": "French", "he": "Hebrew",
            "hi": "Hindi", "it": "Italian", "ja": "Japanese", "ko": "Korean",
            "nl": "Dutch", "pl": "Polish", "pt": "Portuguese", "ru": "Russian",
            "sv": "Swedish", "tr": "Turkish", "zh": "Chinese", "ms": "Malay",
            "sw": "Swahili", "no": "Norwegian", "da": "Danish"
        }
    },
    "sopranotts": {
        "name": "SopranoTTS",
        "languages": {
            "en": "English"
        }
    },
    "neutts-nano": {
        "name": "NeuTTS-Nano",
        "languages": {
            "en": "English", "zh": "Chinese", "ja": "Japanese", "ko": "Korean"
        }
    }
}

def get_tts_languages(tts_model: str) -> dict:
    """Get supported languages for a TTS model"""
    if tts_model in TTS_MODELS:
        return TTS_MODELS[tts_model]["languages"]
    return {"en": "English"}  # Default

def get_all_asr_languages() -> dict:
    """Get all languages supported by ASR"""
    return CANARY_LANGUAGES
