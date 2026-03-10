"""
Worker threads for voice cloning operations.

This module contains QThread subclasses for running blocking operations
in background threads to keep the UI responsive.
"""

from PySide6.QtCore import Signal, QThread

from .models import GenerationRequest, GenerationResult, TTSModel


class VoiceCloneWorker(QThread):
    """Worker thread for voice cloning generation.

    Runs TTS generation in a background thread to prevent UI blocking.
    Communicates results via Qt signals.

    Signals:
        finished: Emitted when generation completes successfully with audio data
        error: Emitted when an error occurs with error message
        progress: Emitted during generation with status message
    """

    finished = Signal(object)  # Audio data (list[float])
    error = Signal(str)
    progress = Signal(str)

    def __init__(
        self,
        tts_manager,
        text: str,
        model: TTSModel | str,
        voice_name: str | None = None,
        reference_audio_path: str | None = None,
    ):
        """Initialize worker with generation parameters.

        Args:
            tts_manager: TTS manager instance for generating speech
            text: Text to synthesize
            model: TTS model ID ('vibevoice' or 'chatterbox-fp16')
            voice_name: Voice preset name for VibeVoice
            reference_audio_path: Path to reference audio for Chatterbox
        """
        super().__init__()
        self.tts_manager = tts_manager
        self.text = text
        self.model = model.value if isinstance(model, TTSModel) else model
        self.voice_name = voice_name
        self.reference_audio_path = reference_audio_path

        # Thread affinity - ensure we're not touching UI from this thread
        self.setObjectName("VoiceCloneWorker")

    def run(self) -> None:
        """Execute voice generation in background thread.

        Calls TTS manager and emits results via signals.
        All UI updates must be done by slot handlers in main thread.
        """
        try:
            self.progress.emit(f"Generating voice with {self.model}...")

            # Use TTS manager to generate speech
            audio = self.tts_manager.generate_speech(
                self.text,
                voice_cloning_audio=self.reference_audio_path,
                voice=self.voice_name if self.model == "vibevoice" else None,
            )

            if len(audio) > 0:
                self.finished.emit(audio)
            else:
                self.error.emit("No audio generated")

        except Exception as e:
            self.error.emit(str(e))
