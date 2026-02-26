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
        self.dtype = 'float32'
        self.chunk_size = 1600  # 100ms chunks
        self.max_duration = 40.0  # Max 40 seconds per utterance
        
        # Available ASR models
        self.available_asr_models = {
            "canary-1b-v2": "Canary 1B v2",
            "parakeet-tdt-v3": "Parakeet TDT v3"
        }
        
        self.model = None
        self.current_asr_model = self.settings_manager.get("asr_model", "canary-1b-v2")
        self.model = None  # Don't load model automatically
        
        # Recording state
        self.is_recording = False
        self.audio_buffer = []
        self.recording_start_time = None
        self.stream = None
        
        # VAD state
        self.vad_monitoring = False
        self.vad_thread = None
        self.audio_queue = queue.Queue()
        self.vad_callback = None
        
        # Energy threshold for VAD
        self.energy_threshold = 0.02
        self.silence_timeout_ms = self.settings_manager.get("silence_timeout_ms", 1000)
        
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
                required_files = ["encoder-model.onnx", "decoder_joint-model.onnx", "vocab.txt"]
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
                if hasattr(result, 'text'):
                    text = result.text
                elif isinstance(result, dict):
                    text = result.get('text', '')
                elif isinstance(result, str):
                    text = result
                else:
                    text = str(result)
            else:
                text = ""
                
            return text.strip()
        except Exception as e:
            print(f"Transcription error: {e}")
            return f"[Transcription error: {str(e)}]"
            
    def start_recording(self):
        """Start manual recording"""
        if self.is_recording:
            return
            
        self.is_recording = True
        self.audio_buffer = []
        self.recording_start_time = time.time()
        
        # Start audio stream
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            blocksize=self.chunk_size,
            callback=self._audio_callback
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
            
        # Combine audio chunks
        audio_data = np.concatenate(self.audio_buffer)
        return audio_data
        
    def _audio_callback(self, indata, frames, time_info, status):
        """Audio stream callback"""
        if self.is_recording:
            self.audio_buffer.append(indata[:, 0].copy())
            
        if self.vad_monitoring:
            self.audio_queue.put(indata[:, 0].copy())
            
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
            callback=self._audio_callback
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
                                    if len(audio_data) > self.sample_rate * 0.3:  # Min 0.3s
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
        terminators = ['.', '?', '!', '。', '？', '！']
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
            else:
                print(f"Failed to switch to {model_name}, keeping current model")
                # Revert to previous model if available
                if self.model is None:
                    self.load_model()