"""
Recording Handlers
Handles start/stop listening and recording state
"""

import time
import logging
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class RecordingHandlers(QObject):
    """Handles recording control actions"""

    # Signals to emit
    recording_started = Signal()
    recording_stopped = Signal()
    processing_started = Signal()
    processing_finished = Signal()
    error_occurred = Signal(str, str)  # title, message

    def __init__(self, voice_processor, main_window, parent=None):
        super().__init__(parent)
        self.voice_processor = voice_processor
        self.main_window = main_window
        self.recording_start_time = 0.0

    def start_listening(self):
        """Start enhanced recording with multi-threading support"""
        self.recording_start_time = time.time()

        try:
            success = self.voice_processor.start_recording()
            if success:
                self.recording_started.emit()
                logger.info("Recording started successfully")
            else:
                self.error_occurred.emit(
                    "Listening Error", "Failed to start listening"
                )
                self.stop_listening()  # Reset state
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.error_occurred.emit("Listening Error", str(e))
            self.stop_listening()

    def stop_listening(self):
        """Stop listening and process the audio"""
        try:
            # Stop recording and get combined audio
            audio_data = self.voice_processor.stop_recording()
            self.recording_stopped.emit()

            if audio_data is not None and len(audio_data) > 0:
                # Start processing
                self.processing_started.emit()

                # Process the audio through main window
                self.main_window.process_audio(audio_data)

                # Log recording statistics
                recording_info = self.voice_processor.get_recording_state()
                duration_sec = len(audio_data) / 16000
                logger.info(
                    f"Processed {duration_sec:.1f}s of audio from "
                    f"{recording_info['segment_count']} segments"
                )
            else:
                self.error_occurred.emit("No Audio", "No audio was recorded")
                self.processing_finished.emit()

        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            self.error_occurred.emit("Recording Error", str(e))
            self.processing_finished.emit()

    def on_processing_finished(self):
        """Handle processing finished event"""
        self.processing_finished.emit()

    def get_elapsed_time(self) -> float:
        """Get elapsed recording time in seconds"""
        if self.recording_start_time > 0:
            return time.time() - self.recording_start_time
        return 0.0

    def manual_activate(self, auto_vad_enabled: bool):
        """
        Manually activate listening (when Auto VAD is disabled)

        Args:
            auto_vad_enabled: Current Auto VAD state
        """
        if not auto_vad_enabled:
            self.start_listening()
