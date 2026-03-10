"""
TTS Service
Handles text-to-speech synthesis operations
"""

import logging

logger = logging.getLogger(__name__)


class TTSService:
    """Service for text-to-speech operations"""

    def __init__(self, tts_manager, settings_manager, main_window):
        self.tts_manager = tts_manager
        self.settings_manager = settings_manager
        self.main_window = main_window

    def synthesize_and_play(
        self,
        text: str,
        model: str = None,
        voice: str = None,
        language: str = None,
        streaming: bool = False,
    ):
        """
        Synthesize text and play via TTS

        Args:
            text: Text to synthesize
            model: TTS model to use (default from settings)
            voice: Voice name for voice-enabled models
            language: Language code for multi-language models
            streaming: Whether to use streaming mode
        """
        if not text:
            return

        # Get settings
        if model is None:
            model = self.settings_manager.get("tts_model", "kittentts")
        if streaming is False:
            streaming = self.settings_manager.get("tts_streaming", False)

        # Get voice/language for VibeVoice
        if model == "vibevoice":
            if voice is None:
                voice = self.settings_manager.get("vibevoice_voice", "Carter")
            if language is None:
                language = self.settings_manager.get("vibevoice_language", "en")

        try:
            # Use voice_worker to synthesize
            if hasattr(self.main_window, "voice_worker"):
                self.main_window.voice_worker.synthesize_and_play(
                    text,
                    model=model,
                    voice=voice,
                    language=language,
                    streaming=streaming,
                )
                logger.info(f"TTS synthesis started for model: {model}")
            else:
                logger.error("voice_worker not available on main_window")
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise

    def get_available_voices(self, model: str) -> list[str]:
        """
        Get available voices for a TTS model

        Args:
            model: TTS model ID

        Returns:
            List of voice names
        """
        voice_sets = {
            "kittentts": [
                "Bella",
                "Jasper",
                "Luna",
                "Bruno",
                "Rosie",
                "Hugo",
                "Kiki",
                "Leo",
            ],
            "vibevoice": [
                "Carter",
                "Emma",
                "Fable",
                "Onyx",
                "Nova",
                "Shimmer",
            ],
        }
        return voice_sets.get(model, [])
