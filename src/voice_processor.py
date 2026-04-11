"""
Voice Processor for Canary Voice AI Assistant
Handles audio recording, VAD (Voice Activity Detection), and ASR transcription
"""

import numpy as np
import sounddevice as sd
import threading
import time
import queue
from pathlib import Path
from typing import Optional, Callable, Any
import librosa

# Import ASR models
from inference.canary_1b_v2 import Canary1Bv2
from inference.parakeet_tdt_v3_inference import LocalParakeetASR


class VoiceProcessor:
    """Handles voice processing including recording, VAD, and transcription"""

    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.sample_rate = 16000
        self.channels = 1
        self.dtype = "float32"
        self.chunk_size = 1600  # 100ms chunks
        
        # Load model-specific max_duration from settings (default 40s for backward compatibility)
        self.max_duration = self._get_model_max_duration()

        # Available ASR models
        self.available_asr_models = {
            "canary-1b-v2": "Canary 1B v2",
            "parakeet-tdt-v3": "Parakeet TDT v3",
            "sensevoice-small": "SenseVoice Small",
            "qwen3-asr": "Qwen3-0.6b (52 langs)",
        }

        self.model = None
        self.current_asr_model = self.settings_manager.get("asr_model", "canary-1b-v2")
        self.model = None  # Don't load model automatically

        # Recording state
        self.is_recording = False
        self.audio_buffer = []
        self.recording_start_time = None
        self.stream = None
        
        # Secondary buffer for SenseVoice Small (triggers at 28.5s to handle 30s limit)
        self.secondary_buffer = []
        self.secondary_buffer_triggered = False
        self.secondary_buffer_thread = None
        self.secondary_buffer_lock = threading.Lock()

        # VAD state
        self.vad_monitoring = False
        self.vad_thread = None
        self.audio_queue = queue.Queue()
        self.vad_callback = None

        # Energy threshold for VAD
        self.energy_threshold = 0.02
        self.silence_timeout_ms = self.settings_manager.get("silence_timeout_ms", 1000)
        
        # Load SVS-specific settings
        self._load_svs_settings()

    def _get_model_max_duration(self) -> float:
        """Get model-specific max duration from settings"""
        current_model = self.settings_manager.get("asr_model", "canary-1b-v2")
        asr_settings = self.settings_manager.get("asr_settings", {})
        model_settings = asr_settings.get(current_model, {})
        return model_settings.get("max_duration_seconds", 40.0)

    def _load_svs_settings(self):
        """Load SenseVoice Small specific settings"""
        asr_settings = self.settings_manager.get("asr_settings", {})
        svs_settings = asr_settings.get("sensevoice-small", {})
        
        # Secondary buffer trigger at 28.5s (leaves 1.5s buffer before 30s limit)
        self.svs_secondary_trigger_seconds = svs_settings.get("secondary_buffer_trigger_seconds", 28.5)
        self.svs_enable_split = svs_settings.get("enable_split_transcription", True)

    def load_model(self, model_name: str = None):
        """Load the specified ASR model"""
        if model_name is None:
            model_name = self.current_asr_model
        else:
            self.current_asr_model = model_name

        try:
            if model_name == "canary-1b-v2":
                model_dir = Path(__file__).parent.parent / "models" / "canary1b"
                if not model_dir.exists():
                    print(f"Warning: Canary model directory not found at {model_dir}")
                    print("Please ensure the model files are downloaded.")
                    return False
                # Force CPU for ASR models
                self.model = Canary1Bv2(model_dir, provider="CPUExecutionProvider")
                print(f"Canary 1B v2 ASR model loaded successfully on CPU")
                return True
            elif model_name == "parakeet-tdt-v3":
                # Check if model files exist
                model_dir = Path(__file__).parent.parent / "models" / "parakeet-tdt-v3"
                required_files = [
                    "encoder-model.onnx",
                    "decoder_joint-model.onnx",
                    "vocab.txt",
                ]
                missing_files = []
                for file in required_files:
                    if not (model_dir / file).exists():
                        missing_files.append(file)

                if missing_files:
                    print(f"Warning: Parakeet model files missing: {missing_files}")
                    print(f"Looking in: {model_dir}")
                    print("Please ensure the model files are downloaded.")
                    return False

                # Force CPU for ASR models
                self.model = LocalParakeetASR()
                print(f"Parakeet TDT v3 ASR model loaded successfully on CPU")
                return True
            elif model_name == "sensevoice-small":
                # Check if model files exist
                model_dir = Path(__file__).parent.parent / "models" / "sensevoicesmall"
                if not model_dir.exists():
                    print(
                        f"Warning: SenseVoiceSmall model directory not found at {model_dir}"
                    )
                    print("Please ensure the model files are downloaded.")
                    return False

                # Import and load SenseVoiceSmall model
                from models.sensevoicesmall.sensevoice_lean import SenseVoiceCTC

                # Force CPU for ASR models
                self.model = SenseVoiceCTC(model_dir, provider="cpu")
                print(f"SenseVoice Small ASR model loaded successfully on CPU")
                return True
            else:
                raise ValueError(f"Unknown ASR model: {model_name}")

        except Exception as e:
            print(f"Error loading {model_name} model: {e}")
            print(f"Falling back to system default (no ASR available)")
            self.model = None
            return False

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribe audio data using current ASR model"""
        if self.model is None:
            # Try to load the current model
            if not self.load_model():
                return "[ASR model not available - please download model files]"

        try:
            # Ensure audio is in correct format
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            # Normalize audio if needed
            if len(audio_data) > 0:
                max_val = np.max(np.abs(audio_data))
                if max_val > 1.0:
                    audio_data = audio_data / max_val

            # Transcribe based on current model
            if self.current_asr_model == "canary-1b-v2":
                language = self.settings_manager.get("target_language", "english")
                text = self.model.transcribe(audio_data, language=language)
            elif self.current_asr_model == "parakeet-tdt-v3":
                # Parakeet model handles language internally
                result = self.model.model.recognize(audio_data)
                if hasattr(result, "text"):
                    text = result.text
                elif isinstance(result, dict):
                    text = result.get("text", "")
                elif isinstance(result, str):
                    text = result
                else:
                    text = str(result)
            elif self.current_asr_model == "sensevoice-small":
                # SenseVoiceSmall supports multiple languages but no translation
                # Use auto-detection or specified language
                lang_map = {
                    "en": "en",
                    "es": "en",  # Map Spanish to English (not supported)
                    "zh": "zh",
                    "ja": "ja",
                    "ko": "ko",
                    "yue": "yue",
                    "auto": "auto",
                }
                language = self.settings_manager.get("target_language", "english")
                sensevoice_lang = lang_map.get(language, "auto")

                # SenseVoiceSmall doesn't support translation, so ignore target_language
                text = self.model.transcribe(
                    audio_data,
                    sample_rate=16000,
                    language=sensevoice_lang,
                    use_itn=True,
                )
            elif self.current_asr_model == "qwen3-asr":
                # Qwen3-ASR - 52 language support
                language = self.settings_manager.get("target_language", "english")
                lang_map = {
                    "english": "en",
                    "chinese": "zh",
                    "german": "de",
                    "french": "fr",
                    "spanish": "es",
                    "japanese": "ja",
                    "korean": "ko",
                    "auto": "auto",
                }
                qwen_lang = lang_map.get(language, "auto")
                text = self.model.transcribe(audio_data, language=qwen_lang)
            else:
                text = ""

            return text.strip()
        except Exception as e:
            print(f"Transcription error: {e}")
            return f"[Transcription error: {str(e)}]"

    def transcribe_split(self, primary_audio: np.ndarray, secondary_audio: np.ndarray) -> str:
        """
        Transcribe split audio buffers for SenseVoice Small (handles 30s limit).
        Transcribes each chunk separately and intelligently concatenates the results.
        """
        try:
            # Transcribe primary buffer (first ~28.5 seconds)
            primary_text = self.transcribe(primary_audio) if primary_audio is not None else ""
            
            # Transcribe secondary buffer (remaining audio)
            secondary_text = self.transcribe(secondary_audio) if secondary_audio is not None else ""
            
            # Intelligent concatenation
            combined = self._concatenate_transcriptions(primary_text, secondary_text)
            
            print(f"[SVS] Split transcription: primary='{primary_text[:50]}...' secondary='{secondary_text[:50]}...'")
            print(f"[SVS] Combined: '{combined[:50]}...'")
            
            return combined
            
        except Exception as e:
            print(f"Split transcription error: {e}")
            return f"[Split transcription error: {str(e)}]"

    def _concatenate_transcriptions(self, primary: str, secondary: str) -> str:
        """
        Intelligently concatenate two transcriptions with proper spacing and punctuation.
        """
        if not primary:
            return secondary
        if not secondary:
            return primary
        
        # Clean up both texts
        primary = primary.strip()
        secondary = secondary.strip()
        
        # Check if primary ends with punctuation
        if primary.endswith(('.', '!', '?', '。', '！', '？', ',', ';', ':')):
            # Already has proper ending, just add space and secondary
            return f"{primary} {secondary}"
        else:
            # No clear ending, add period and secondary
            return f"{primary}. {secondary}"

    def start_recording(self):
        """Start manual recording"""
        if self.is_recording:
            return

        self.is_recording = True
        self.audio_buffer = []
        self.secondary_buffer = []
        self.secondary_buffer_triggered = False
        self.recording_start_time = time.time()

        # Start audio stream
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            blocksize=self.chunk_size,
            callback=self._audio_callback,
        )
        self.stream.start()

    def stop_recording(self) -> Optional[np.ndarray]:
        """Stop manual recording and return audio data"""
        if not self.is_recording:
            return None

        if self.stream:
            self.stream.stop()
            self.stream.close()
        self.is_recording = False

        if not self.audio_buffer:
            return None

        # For SenseVoice Small with split transcription
        if (self.current_asr_model == "sensevoice-small" and 
            self.svs_enable_split and 
            self.secondary_buffer_triggered and 
            self.secondary_buffer):
            # Return a tuple of (primary_buffer_audio, secondary_buffer_audio)
            primary_audio = np.concatenate(self.audio_buffer)
            secondary_audio = np.concatenate(self.secondary_buffer)
            return (primary_audio, secondary_audio)

        # Combine audio chunks
        audio_data = np.concatenate(self.audio_buffer)
        return audio_data
    
    def stop_recording_split(self) -> tuple:
        """Stop recording and return both primary and secondary buffers for SVS"""
        if not self.is_recording:
            return (None, None)
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
        self.is_recording = False
        
        primary = np.concatenate(self.audio_buffer) if self.audio_buffer else None
        secondary = np.concatenate(self.secondary_buffer) if self.secondary_buffer else None
        
        return (primary, secondary)

    def _audio_callback(self, indata, frames, time_info, status):
        """Audio stream callback"""
        if self.is_recording:
            # Check if we need to trigger secondary buffer for SenseVoice Small
            if (self.current_asr_model == "sensevoice-small" and 
                self.svs_enable_split and 
                not self.secondary_buffer_triggered):
                # Check recording duration
                if self.recording_start_time:
                    elapsed = time.time() - self.recording_start_time
                    if elapsed >= self.svs_secondary_trigger_seconds:
                        # Trigger secondary buffer
                        self._trigger_secondary_buffer()
            
            # Add to appropriate buffer
            if (self.current_asr_model == "sensevoice-small" and 
                self.svs_enable_split and 
                self.secondary_buffer_triggered):
                # After trigger, add to secondary buffer
                self.secondary_buffer.append(indata[:, 0].copy())
            else:
                # Primary buffer
                self.audio_buffer.append(indata[:, 0].copy())

        if self.vad_monitoring:
            self.audio_queue.put(indata[:, 0].copy())
    
    def _trigger_secondary_buffer(self):
        """Trigger secondary buffer for SVS split transcription"""
        with self.secondary_buffer_lock:
            if not self.secondary_buffer_triggered:
                self.secondary_buffer_triggered = True
                print(f"[SVS] Secondary buffer triggered at {self.svs_secondary_trigger_seconds}s")
                # Start a new buffer for the second chunk
                self.secondary_buffer = []

    def start_vad_monitoring(self, callback: Optional[Callable] = None):
        """Start VAD monitoring for automatic trigger"""
        if self.vad_monitoring:
            return

        self.vad_monitoring = True
        self.vad_callback = callback
        self.vad_thread = threading.Thread(target=self._vad_monitor_loop, daemon=True)
        self.vad_thread.start()

    def stop_vad_monitoring(self):
        """Stop VAD monitoring"""
        self.vad_monitoring = False
        if self.vad_thread:
            self.vad_thread.join(timeout=1.0)

    def _vad_monitor_loop(self):
        """Main VAD monitoring loop"""
        audio_buffer = []
        last_speech_time = time.time()
        speech_detected = False

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            blocksize=self.chunk_size,
            callback=self._audio_callback,
        ):
            while self.vad_monitoring:
                try:
                    # Get audio chunk from queue
                    chunk = self.audio_queue.get(timeout=0.1)

                    # Check energy level
                    energy = np.sqrt(np.mean(chunk**2))
                    current_time = time.time()

                    if energy > self.energy_threshold:
                        # Speech detected
                        audio_buffer.append(chunk)
                        speech_detected = True
                        last_speech_time = current_time
                    else:
                        # Silence detected
                        if speech_detected:
                            silence_duration = (current_time - last_speech_time) * 1000
                            if silence_duration >= self.silence_timeout_ms:
                                # Process the accumulated audio
                                if audio_buffer:
                                    audio_data = np.concatenate(audio_buffer)
                                    if (
                                        len(audio_data) > self.sample_rate * 0.3
                                    ):  # Min 0.3s
                                        if self.vad_callback:
                                            self.vad_callback(audio_data)
                                        else:
                                            # Default behavior - emit signal or process directly
                                            pass

                                # Reset for next utterance
                                audio_buffer = []
                                speech_detected = False

                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"VAD monitoring error: {e}")
                    continue

    def analyze_energy(self, audio_chunk: np.ndarray) -> float:
        """Analyze energy level of audio chunk"""
        return np.sqrt(np.mean(audio_chunk**2))

    def has_sentence_boundary(self, text: str) -> bool:
        """Check if text ends with sentence boundary"""
        if not text:
            return False

        clean_text = text.strip()
        terminators = [".", "?", "!", "。", "？", "！"]
        return any(clean_text.endswith(t) for t in terminators)

    def get_audio_duration(self, audio_data: np.ndarray) -> float:
        """Get audio duration in seconds"""
        return len(audio_data) / self.sample_rate

    def get_available_asr_models(self) -> dict:
        """Get available ASR models"""
        return self.available_asr_models.copy()

    def get_current_asr_model(self) -> str:
        """Get current ASR model name"""
        return self.current_asr_model

    def switch_asr_model(self, model_name: str):
        """Switch to a different ASR model"""
        if model_name not in self.available_asr_models:
            raise ValueError(f"Unknown ASR model: {model_name}")

        if model_name != self.current_asr_model:
            print(f"Switching ASR model from {self.current_asr_model} to {model_name}")
            success = self.load_model(model_name)
            if success:
                # Save to settings
                self.settings_manager.set("asr_model", model_name)
                self.settings_manager.save_settings()
                # Reload model-specific settings
                self.max_duration = self._get_model_max_duration()
                self._load_svs_settings()
                print(f"Updated max_duration to {self.max_duration}s for {model_name}")
            else:
                print(f"Failed to switch to {model_name}, keeping current model")
                # Revert to previous model if available
                if self.model is None:
                    self.load_model()
