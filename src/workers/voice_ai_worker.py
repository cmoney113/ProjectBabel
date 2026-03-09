"""
Voice AI Worker - Background processing for voice transcription and response generation
Handles the complete voice AI pipeline: ASR -> Translation -> LLM -> TTS
"""

import asyncio
import logging
from typing import Optional
from PySide6.QtCore import QThread, Signal


class VoiceAIWorker(QThread):
    """Background worker for voice processing with language detection and translation"""

    transcription_ready = Signal(str)
    response_ready = Signal(str)
    processing_started = Signal()
    processing_finished = Signal()
    error_occurred = Signal(str)

    def __init__(
        self,
        voice_processor,
        llm_manager,
        tts_manager,
        web_search_manager,
        settings_manager=None,
    ):
        super().__init__()
        self.voice_processor = voice_processor
        self.llm_manager = llm_manager
        self.tts_manager = tts_manager
        self.web_search_manager = web_search_manager
        self.settings_manager = settings_manager

        # Processing state
        self.current_audio = None
        self.is_dictation_mode = False
        self.conversation_history = []
        self.translation_enabled = False
        self.dictation_window_id = None  # Window ID for dictation injection

        # Pipeline configuration
        from src.pipeline import get_voice_pipeline

        self.pipeline = (
            get_voice_pipeline(settings_manager) if settings_manager else None
        )
        self.current_verbosity = "balanced"
        self.target_language = "en"
        self.current_tts_model = "chatterbox-fp16"

        # Logger
        self.logger = logging.getLogger(__name__)

    def set_audio(self, audio_data):
        """Set audio data for processing"""
        self.current_audio = audio_data

    def set_dictation_mode(self, enabled: bool):
        """Enable/disable dictation mode"""
        self.is_dictation_mode = enabled

    def set_verbosity(self, verbosity: str):
        """Set response verbosity level"""
        self.current_verbosity = verbosity

    def set_target_language(self, lang: str):
        """Set target language for translation"""
        self.target_language = lang

    def set_translation_enabled(self, enabled: bool):
        """Enable/disable translation"""
        self.translation_enabled = enabled

    def set_tts_model(self, model: str):
        """Set current TTS model"""
        self.current_tts_model = model

    def set_tts_voice(self, voice: str):
        """Set KittenTTS voice"""
        self.current_tts_voice = voice

    def set_dictation_window(self, window_id: int):
        """Set window ID for dictation injection"""
        self.dictation_window_id = window_id

    def run(self):
        """Main processing loop - handles complete voice AI pipeline"""
        if self.current_audio is None:
            return

        try:
            self.processing_started.emit()

            # Transcribe audio with language detection
            transcription_result = self.voice_processor.transcribe_with_language(
                self.current_audio
            )
            transcription = transcription_result.text
            detected_language = transcription_result.detected_language

            self.transcription_ready.emit(transcription)

            # Log language detection info
            self.logger.info(
                f"Detected language: {detected_language} (confidence: {transcription_result.confidence})"
            )

            if self.is_dictation_mode:
                # Dictation mode: translate if needed, then clean up
                self._process_dictation(transcription, detected_language)
            else:
                # Voice AI mode: translate if needed, then process via iFlow
                self._process_voice_ai(transcription, detected_language)

            self.processing_finished.emit()

        except Exception as e:
            self.logger.error(f"Voice processing error: {e}")
            self.error_occurred.emit(str(e))
            self.processing_finished.emit()

    def _process_dictation(self, transcription: str, detected_language: str):
        """Process dictation mode with optional translation"""
        try:
            # Get async event loop
            loop = self._get_event_loop()

            if self.pipeline:
                result = loop.run_until_complete(
                    self.pipeline.process_dictation(
                        audio_data=transcription,
                        detected_language=detected_language,
                        target_language=self.target_language,
                    )
                )
                processed_text = result.output_text
            else:
                # Fallback to old method
                processed_text = self.llm_manager.process_dictation(transcription)

            self.response_ready.emit(processed_text)
            # Output to wbind for typing, focusing window first if selected
            if self.dictation_window_id:
                self.tts_manager.focus_and_type(
                    self.dictation_window_id, processed_text
                )
            else:
                self.tts_manager.type_text(processed_text)

        except Exception as e:
            self.logger.error(f"Dictation processing error: {e}")
            self.error_occurred.emit(str(e))

    def _process_voice_ai(self, transcription: str, detected_language: str):
        """Process voice AI mode with optional translation"""
        try:
            # Get async event loop
            loop = self._get_event_loop()

            if self.pipeline:
                result = loop.run_until_complete(
                    self.pipeline.process_voice_ai(
                        audio_data=transcription,
                        detected_language=detected_language,
                        target_language=self.target_language,
                        tts_model=self.current_tts_model,
                        verbosity=self.current_verbosity,
                    )
                )
                response = result.output_text
            else:
                # Fallback to old method
                should_search = self.web_search_manager.should_perform_search(
                    transcription, confidence_threshold=0.85
                )
                if should_search:
                    search_results = self.web_search_manager.search(transcription)
                    response = self.llm_manager.generate_response_with_context(
                        transcription, self.conversation_history, search_results
                    )
                else:
                    response = self.llm_manager.generate_response_with_context(
                        transcription, self.conversation_history
                    )

            self.response_ready.emit(response)
            self.conversation_history.append({"role": "user", "content": transcription})
            self.conversation_history.append({"role": "assistant", "content": response})

            # Speak response via TTS - pass voice and streaming settings
            streaming = self.settings_manager.get("tts_streaming", True)
            if self.current_tts_model == "kittentts" and hasattr(
                self, "current_tts_voice"
            ):
                self.tts_manager.speak(
                    response, voice=self.current_tts_voice, streaming=streaming
                )
            elif self.current_tts_model == "vibevoice" and hasattr(
                self, "current_tts_voice"
            ):
                self.tts_manager.speak(
                    response, voice=self.current_tts_voice, streaming=streaming
                )
            else:
                self.tts_manager.speak(response, streaming=streaming)

        except Exception as e:
            self.logger.error(f"Voice AI processing error: {e}")
            self.error_occurred.emit(str(e))

    def _get_event_loop(self):
        """Get or create async event loop"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop
