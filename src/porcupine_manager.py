"""
Porcupine Wake Word Manager
Handles wake word detection for Voice AI and Dictation modes
"""

import os
import threading
import pvporcupine
import sounddevice as sd
from pathlib import Path


class PorcupineWakeWord:
    """Porcupine wake word detection - runs in separate thread"""

    def __init__(self, ppn_path: str, api_key: str, keyword: str = "custom"):
        self.ppn_path = ppn_path
        self.api_key = api_key
        self.keyword = keyword
        self.porcupine = None
        self.stream = None
        self.running = False
        self.callback = None
        self.detection_thread = None
        self.error_callback = None

    def start(self, callback, error_callback=None):
        """Start listening for wake word"""
        if self.running:
            return

        self.callback = callback
        self.error_callback = error_callback

        try:
            self.porcupine = pvporcupine.create(
                keyword_paths=[self.ppn_path], access_key=self.api_key
            )

            self.running = True
            self.detection_thread = threading.Thread(
                target=self._detection_loop, daemon=True
            )
            self.detection_thread.start()
            print(f"Porcupine wake word '{self.keyword}' started")
            return True

        except Exception as e:
            print(f"Failed to start Porcupine: {e}")
            self.porcupine = None
            if error_callback:
                error_callback(str(e))
            return False

    def _detection_loop(self):
        """Main detection loop running in separate thread"""
        try:

            def audio_callback(indata, frames, time_info, status):
                if status:
                    print(f"Audio callback status: {status}")

                audio_data = indata.flatten()
                result = self.porcupine.process(audio_data)

                if result >= 0:
                    print(f"Wake word '{self.keyword}' detected!")
                    if self.callback:
                        self.callback()
                    self.running = False
                    self._cleanup()
                    if self.callback and self.error_callback is None:
                        threading.Timer(0.5, self._restart_detection).start()

            self.stream = sd.InputStream(
                channels=1,
                samplerate=self.porcupine.sample_rate,
                blocksize=self.porcupine.frame_length,
                callback=audio_callback,
            )
            self.stream.start()

            while self.running:
                sd.sleep(100)

        except Exception as e:
            print(f"Detection loop error: {e}")
            if self.error_callback:
                self.error_callback(str(e))
        finally:
            self._cleanup()

    def _restart_detection(self):
        """Restart detection after trigger"""
        if self.callback and not self.running:
            self.start(self.callback, self.error_callback)

    def _cleanup(self):
        """Clean up resources"""
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass
            self.stream = None

    def stop(self):
        """Stop listening for wake word"""
        self.running = False
        if self.detection_thread:
            self.detection_thread.join(timeout=2)
        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None
        print(f"Porcupine wake word '{self.keyword}' stopped")


class WakeWordManager:
    """Manages multiple wake word detectors for different modes"""

    def __init__(self):
        base_path = Path("/home/craig/new-projects/voice_ai/assets")

        self.voice_ai_wakeword = PorcupineWakeWord(
            ppn_path=str(base_path / "I-wanna-talk.ppn"),
            api_key="ATlm9W8c1Qu/tfw5sN5yU8wVYdYb6oorhr4K227kv+vGwteLaUTOuQ==",
            keyword="voice-ai",
        )

        self.dictation_wakeword = PorcupineWakeWord(
            ppn_path=str(base_path / "I-have-a-thought.ppn"),
            api_key="d2w3Jxzl9Nqr+R9f4xJCjUdj+gk1pClk3tWIuQOqt/KkSteanOAkzw==",
            keyword="dictation",
        )

        self.active_callback = None
        self.error_callback = None
        self.current_mode = None

    def set_error_callback(self, callback):
        """Set error callback for wake word failures"""
        self.error_callback = callback
        self.voice_ai_wakeword.error_callback = callback
        self.dictation_wakeword.error_callback = callback

    def start_voice_ai_mode(self, callback):
        """Start listening for Voice AI wake word"""
        self.stop_all()
        self.current_mode = "voice-ai"
        self.active_callback = callback
        self.voice_ai_wakeword.start(callback, self.error_callback)

    def start_dictation_mode(self, callback):
        """Start listening for Dictation wake word"""
        self.stop_all()
        self.current_mode = "dictation"
        self.active_callback = callback
        self.dictation_wakeword.start(callback, self.error_callback)

    def restart_current(self):
        """Restart current wake word mode"""
        if self.current_mode == "voice-ai" and self.active_callback:
            self.voice_ai_wakeword.start(self.active_callback, self.error_callback)
        elif self.current_mode == "dictation" and self.active_callback:
            self.dictation_wakeword.start(self.active_callback, self.error_callback)

    def stop_all(self):
        """Stop all wake word detection"""
        self.voice_ai_wakeword.stop()
        self.dictation_wakeword.stop()
        self.active_callback = None
        self.current_mode = None
