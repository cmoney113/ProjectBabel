from src.model_registry import ModelRegistry


# Convenience alias for backward compatibility
CANARY_LANGUAGES = ModelRegistry.get_asr_languages()
TTS_MODELS = ModelRegistry.TTS_MODELS


def get_tts_languages(tts_model: str):
    """Get supported languages for a TTS model from ModelRegistry"""
    model = ModelRegistry.get_model(tts_model)
    if model:
        return model.languages
    return {"en": "English"}


def get_all_asr_languages():
    """Get all languages supported by ASR from ModelRegistry"""
    return ModelRegistry.get_asr_languages()
