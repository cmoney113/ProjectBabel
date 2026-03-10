"""
Model Handlers
Handles ASR and TTS model selection changes
"""

import logging
from PySide6.QtCore import QObject
from qfluentwidgets import InfoBar

logger = logging.getLogger(__name__)


class ModelHandlers(QObject):
    """Handles model selection changes"""

    def __init__(self, voice_processor, tts_manager, settings_manager, parent=None):
        super().__init__(parent)
        self.voice_processor = voice_processor
        self.tts_manager = tts_manager
        self.settings_manager = settings_manager

    def on_asr_model_changed(self, model_id: str, model_name: str):
        """
        Handle ASR model selection change

        Args:
            model_id: The model identifier
            model_name: Human-readable model name
        """
        if not model_id:
            return

        current_model = self.voice_processor.get_current_asr_model()
        if model_id == current_model:
            return

        try:
            self.voice_processor.switch_asr_model(model_id)
            InfoBar.success(
                "ASR Model Changed",
                f"Switched to {model_name}",
                parent=self.parent(),
                duration=2000,
            )
            logger.info(f"ASR model switched to: {model_id}")
        except Exception as e:
            logger.error(f"Failed to switch ASR model: {e}")
            InfoBar.error(
                "ASR Model Error",
                f"Failed to switch ASR model: {str(e)}",
                parent=self.parent(),
                duration=3000,
            )

    def on_tts_model_changed(
        self, model_id: str, model_name: str, voice: str = None, language: str = None
    ):
        """
        Handle TTS model selection change

        Args:
            model_id: The model identifier
            model_name: Human-readable model name
            voice: Optional voice name for voice-enabled models
            language: Optional language code
        """
        if not model_id:
            return

        current_model = self.tts_manager.get_current_tts_model()
        if model_id == current_model:
            return

        try:
            self.tts_manager.switch_tts_model(model_id)

            # Save voice settings if provided
            if voice and model_id == "kittentts":
                self.settings_manager.set("kittentts_voice", voice)
                InfoBar.info(
                    "KittenTTS Voice",
                    f"Voice: {voice}",
                    parent=self.parent(),
                    duration=1500,
                )
            elif voice and model_id == "vibevoice":
                self.settings_manager.set("vibevoice_voice", voice)
                self.settings_manager.set("vibevoice_language", language or "en")
                InfoBar.info(
                    "VibeVoice Voice",
                    f"Voice: {voice}, Language: {language or 'en'}",
                    parent=self.parent(),
                    duration=1500,
                )
            else:
                InfoBar.success(
                    "TTS Model Changed",
                    f"Switched to {model_name}",
                    parent=self.parent(),
                    duration=2000,
                )

            self.tts_manager.set_current_tts_model(model_id)
            self.settings_manager.set("tts_model", model_id)
            logger.info(f"TTS model switched to: {model_id}")

        except Exception as e:
            logger.error(f"Failed to switch TTS model: {e}")
            InfoBar.error(
                "TTS Model Error",
                f"Failed to switch TTS model: {str(e)}",
                parent=self.parent(),
                duration=3000,
            )

    def on_kittentts_voice_changed(self, voice: str):
        """Handle KittenTTS voice change"""
        self.settings_manager.set("kittentts_voice", voice)
        logger.info(f"KittenTTS voice changed to: {voice}")

    def on_vibevoice_voice_changed(self, voice: str, language: str = "en"):
        """Handle VibeVoice voice change"""
        self.settings_manager.set("vibevoice_voice", voice)
        self.settings_manager.set("vibevoice_language", language)
        logger.info(f"VibeVoice voice changed to: {voice}, language: {language}")
