"""
Enhanced Voice Processor with Multi-Threading Recording and Language Detection
Uses ASR FastAPI server for transcription with proper language detection
"""

import numpy as np
import sounddevice as sd
import threading
import time
import queue
import base64
import io
import soundfile as sf
from pathlib import Path
from typing import Optional, Callable, Any, List, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime
import requests


# ASR Server configuration
ASR_SERVER_URL = "http://localhost:8710"


@dataclass
class AudioSegment:
    """Represents a recorded audio segment with timing information"""

    audio_data: np.ndarray
    start_time: float  # Unix timestamp
    duration: float  # Duration in seconds
    segment_id: int
    is_primary: bool = True


@dataclass
class TranscriptionResult:
    """Result from ASR transcription including detected language"""

    text: str
    detected_language: str
    confidence: Optional[float] = None


class RecordingWorker(threading.Thread):
    """Worker thread for recording audio segments beyond 25.5 seconds"""

    SEGMENT_DURATION = 25.0  # 25 seconds per worker
    OVERLAP_DURATION = 0.5  # 0.5 second overlap for seamless joining

    def __init__(self, worker_id: int, start_time: float, audio_callback: Callable):
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.start_time = start_time
        self.audio_callback = audio_callback
        self.audio_buffer = []
        self.is_recording = True
        self.segment_complete = False
        self.logger = logging.getLogger(f"RecordingWorker-{worker_id}")

    def run(self):
        """Main recording loop for this worker"""
        self.logger.info(
            f"Worker {self.worker_id} started recording at {self.start_time:.3f}s"
        )

        try:
            with sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype="float32",
                blocksize=1600,  # 100ms chunks
                callback=self._audio_callback,
            ):
                while (
                    self.is_recording and len(self.audio_buffer) < 400
                ):  # 25 seconds at 16kHz
                    time.sleep(0.1)  # Check every 100ms

                # Final processing
                if self.audio_buffer:
                    audio_data = np.concatenate(self.audio_buffer)
                    segment = AudioSegment(
                        audio_data=audio_data,
                        start_time=self.start_time,
                        duration=len(audio_data) / 16000.0,
                        segment_id=self.worker_id,
                        is_primary=False,
                    )
                    self.audio_callback(segment)

        except Exception as e:
            self.logger.error(f"Worker {self.worker_id} error: {e}")
        finally:
            self.segment_complete = True
            self.logger.info(f"Worker {self.worker_id} completed")

    def _audio_callback(self, indata, frames, time_info, status):
        """Audio callback for this worker"""
        if self.is_recording:
            self.audio_buffer.append(indata[:, 0].copy())

    def stop_recording(self):
        """Stop this worker's recording"""
        self.is_recording = False


class EnhancedVoiceProcessor:
    """Enhanced voice processor with multi-threading and unlimited recording support"""

    # Constants
    SAMPLE_RATE = 16000
    CHANNELS = 1
    DTYPE = "float32"
    CHUNK_SIZE = 1600  # 100ms chunks
    MAX_PRIMARY_DURATION = 25.5  # 25.5 seconds for primary buffer (default)

    def __init__(self, settings_manager, waveform_widget=None):
        self.settings_manager = settings_manager
        self.waveform_widget = waveform_widget

        # Logging (needed by _load_model_settings)
        self.logger = logging.getLogger("EnhancedVoiceProcessor")

        # ASR models (same as before)
        self.available_asr_models = {
            "canary-1b-v2": "Canary 1B v2",
            "parakeet-tdt-v3": "Parakeet TDT v3",
            "sensevoice-small": "SenseVoice Small",
            "qwen3-asr": "Qwen3-0.6b (52 langs)",
        }
        self.current_asr_model = settings_manager.get("asr_model", "canary-1b-v2")
        self.model = None

        # Load model-specific settings (requires current_asr_model and logger)
        self._load_model_settings()

        # Recording state
        self.is_recording = False
        self.recording_start_time = None
        self.audio_buffer = []  # Primary buffer (first N seconds based on model)
        self.stream = None

        # Multi-threading components
        self.workers = []  # List of RecordingWorker threads
        self.current_worker_id = 0
        self.worker_lock = threading.Lock()

        # Audio segments for final processing
        self.audio_segments = []

        # Stream initialization signaling (fixes race condition)
        self._stream_ready = threading.Event()
        self._stream_error = None
        self.segment_lock = threading.Lock()

    def _load_model_settings(self):
        """Load model-specific settings from settings.json"""
        asr_settings = self.settings_manager.get("asr_settings", {})
        
        # Get max_duration for current model (default 25.5s for backward compat)
        model_settings = asr_settings.get(self.current_asr_model, {})
        self.max_primary_duration = model_settings.get("max_duration_seconds", 25.5)
        
        # For SenseVoice Small, use secondary buffer trigger settings
        svs_settings = asr_settings.get("sensevoice-small", {})
        self.svs_secondary_trigger = svs_settings.get("secondary_buffer_trigger_seconds", 28.5)
        self.svs_enable_split = svs_settings.get("enable_split_transcription", True)
        
        # Use shorter duration for SVS (model constraint: 30s max)
        if self.current_asr_model == "sensevoice-small":
            self.MAX_PRIMARY_DURATION = self.svs_secondary_trigger
        else:
            self.MAX_PRIMARY_DURATION = self.max_primary_duration
        
        self.logger.info(f"Model '{self.current_asr_model}': max_primary_duration={self.MAX_PRIMARY_DURATION}s")

    def load_model(self, model_name: str = None):
        """Load the specified ASR model via FastAPI server"""
        if model_name is None:
            model_name = self.current_asr_model
        else:
            self.current_asr_model = model_name

        try:
            # Call the FastAPI server to load the model
            response = requests.post(
                f"{ASR_SERVER_URL}/load", params={"model": model_name}, timeout=30
            )
            if response.status_code == 200:
                self.logger.info(
                    f"ASR model '{model_name}' loaded successfully via FastAPI server"
                )
                return True
            else:
                self.logger.error(f"Failed to load ASR model: {response.text}")
                return False
        except requests.exceptions.ConnectionError:
            self.logger.error("Cannot connect to ASR server. Is it running?")
            return False
        except Exception as e:
            self.logger.error(f"Error loading ASR model: {e}")
            return False

    def start_recording(self) -> bool:
        """Start enhanced recording with multi-threading support"""
        if self.is_recording:
            return False

        self.logger.info("Starting enhanced recording")

        # Reset state
        self._stream_ready.clear()
        self._stream_error = None
        self.is_recording = True
        self.recording_start_time = time.time()
        self.audio_buffer = []
        self.audio_segments = []
        self.workers = []
        self.current_worker_id = 0

        # Start primary recording thread
        self.primary_thread = threading.Thread(
            target=self._primary_recording_loop, daemon=True
        )
        self.primary_thread.start()

        # Wait for stream to actually open (with timeout)
        # This fixes the race condition where start_recording() returned
        # before the sd.InputStream was initialized
        if not self._stream_ready.wait(timeout=2.0):
            self.logger.error("Timeout waiting for audio stream to initialize")
            self.is_recording = False
            return False

        # Check if stream opened successfully
        if self._stream_error:
            self.logger.error(f"Audio stream failed to open: {self._stream_error}")
            self.is_recording = False
            return False

        # Update waveform widget if available
        if self.waveform_widget:
            self.waveform_widget.set_state(self.waveform_widget.STATE_RECORDING)

        return True

    def _primary_recording_loop(self):
        """Primary recording loop - duration based on ASR model"""
        # Calculate max chunks based on model-specific duration
        # At 16kHz with 100ms chunks (1600 samples), we get 10 chunks per second
        max_chunks = int(self.MAX_PRIMARY_DURATION * 10)
        
        self.logger.info(f"Primary recording thread started (max {self.MAX_PRIMARY_DURATION}s)")

        try:
            with sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype=self.DTYPE,
                blocksize=self.CHUNK_SIZE,
                callback=self._audio_callback,
            ):
                # Signal that stream is ready - fixes race condition
                self._stream_ready.set()
                
                while self.is_recording and len(self.audio_buffer) < max_chunks:
                    time.sleep(0.1)  # Check every 100ms

                    # Check if we need to spawn a worker (at 90% of max duration)
                    current_duration = len(self.audio_buffer) * 0.1  # Approximate duration
                    trigger_threshold = self.MAX_PRIMARY_DURATION * 0.9
                    if current_duration >= trigger_threshold and not self.workers:
                        self._spawn_worker()

                # Primary recording complete
                if self.audio_buffer:
                    primary_audio = np.concatenate(self.audio_buffer)
                    primary_segment = AudioSegment(
                        audio_data=primary_audio,
                        start_time=self.recording_start_time,
                        duration=len(primary_audio) / self.SAMPLE_RATE,
                        segment_id=0,
                        is_primary=True,
                    )

                    with self.segment_lock:
                        self.audio_segments.append(primary_segment)

                    self.logger.info(
                        f"Primary recording complete: {len(primary_audio) / self.SAMPLE_RATE:.2f}s"
                    )

        except Exception as e:
            self.logger.error(f"Primary recording error: {e}")
            # Signal error and unblock waiter
            self._stream_error = e
            self._stream_ready.set()

    def _spawn_worker(self):
        """Spawn a new worker thread for extended recording"""
        with self.worker_lock:
            self.current_worker_id += 1
            worker_start_time = time.time()

            worker = RecordingWorker(
                worker_id=self.current_worker_id,
                start_time=worker_start_time,
                audio_callback=self._handle_worker_segment,
            )

            self.workers.append(worker)
            worker.start()

            self.logger.info(
                f"Spawned worker {self.current_worker_id} at {worker_start_time:.3f}s"
            )

    def _handle_worker_segment(self, segment: AudioSegment):
        """Handle completed audio segment from worker thread"""
        with self.segment_lock:
            self.audio_segments.append(segment)
            self.logger.info(
                f"Received segment {segment.segment_id}: {segment.duration:.2f}s"
            )

    def _audio_callback(self, indata, frames, time_info, status):
        """Audio callback for primary recording"""
        if status:
            self.logger.warning(f"Audio callback status: {status}")
            
        if self.is_recording:
            audio_chunk = indata[:, 0].copy()
            self.audio_buffer.append(audio_chunk)

            # Send to waveform widget if available
            if self.waveform_widget:
                self.waveform_widget.add_audio_data(audio_chunk)

    def stop_recording(self) -> Optional[np.ndarray]:
        """Stop recording and return combined audio data"""
        if not self.is_recording:
            return None

        self.logger.info("Stopping enhanced recording")
        self.is_recording = False

        # Wait for primary thread to complete
        if hasattr(self, "primary_thread"):
            self.primary_thread.join(timeout=2.0)

        # Stop all worker threads
        with self.worker_lock:
            for worker in self.workers:
                worker.stop_recording()

            # Wait for workers to complete
            for worker in self.workers:
                worker.join(timeout=2.0)

        # Update waveform widget
        if self.waveform_widget:
            self.waveform_widget.set_state(self.waveform_widget.STATE_PROCESSING)

        # Combine all audio segments
        return self._combine_audio_segments()

    def _combine_audio_segments(self) -> Optional[np.ndarray]:
        """Intelligently combine all audio segments"""
        with self.segment_lock:
            if not self.audio_segments:
                self.logger.warning("No audio segments to combine")
                return None

            # Sort segments by start time
            sorted_segments = sorted(self.audio_segments, key=lambda x: x.start_time)

            self.logger.info(f"Combining {len(sorted_segments)} segments")

            # Start with primary segment
            combined_audio = sorted_segments[0].audio_data

            # Add secondary segments with intelligent alignment
            for i, segment in enumerate(sorted_segments[1:], 1):
                if segment.is_primary:
                    continue  # Skip non-primary segments (shouldn't happen)

                # Calculate expected overlap
                prev_end_time = (
                    sorted_segments[i - 1].start_time + sorted_segments[i - 1].duration
                )
                current_start_time = segment.start_time
                overlap_duration = max(0, prev_end_time - current_start_time)

                self.logger.debug(f"Segment {i}: overlap {overlap_duration:.3f}s")

                # Handle overlap intelligently
                if overlap_duration > 0.1:  # Significant overlap
                    # Remove overlap from current segment
                    overlap_samples = int(overlap_duration * self.SAMPLE_RATE)
                    if overlap_samples < len(segment.audio_data):
                        trimmed_audio = segment.audio_data[overlap_samples:]
                        combined_audio = np.concatenate([combined_audio, trimmed_audio])
                        self.logger.debug(
                            f"Trimmed {overlap_samples} samples from segment {i}"
                        )
                    else:
                        # Entire segment is overlap, skip it
                        self.logger.warning(
                            f"Segment {i} is entirely overlap, skipping"
                        )
                else:
                    # No significant overlap, just append
                    combined_audio = np.concatenate(
                        [combined_audio, segment.audio_data]
                    )

            total_duration = len(combined_audio) / self.SAMPLE_RATE
            self.logger.info(f"Combined audio duration: {total_duration:.2f}s")

            return combined_audio

    def transcribe_with_language(
        self, audio_data: np.ndarray, target_language: str = None
    ) -> TranscriptionResult:
        """
        Transcribe audio data using ASR FastAPI server and return detected language

        Args:
            audio_data: Audio numpy array
            target_language: Target language for translation (if None, uses settings)

        Returns:
            TranscriptionResult with text, detected_language, and confidence
        """
        try:
            # Ensure audio is in correct format
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            # Normalize if needed
            if len(audio_data) > 0:
                max_val = np.max(np.abs(audio_data))
                if max_val > 1.0:
                    audio_data = audio_data / max_val

            # Convert audio to base64
            buffer = io.BytesIO()
            sf.write(buffer, audio_data, self.SAMPLE_RATE, format="WAV")
            buffer.seek(0)
            audio_base64 = base64.b64encode(buffer.read()).decode("utf-8")

            # Get source language from settings
            source_language = self.settings_manager.get("target_language", "en")

            # Build request - ASR should detect language and return it
            request_json = {
                "audio_data": audio_base64,
                "model": self.current_asr_model,
                "sample_rate": self.SAMPLE_RATE,
                "language": source_language,
                "detect_language": True,  # Request language detection
            }

            # Call the FastAPI server with language detection enabled
            response = requests.post(
                f"{ASR_SERVER_URL}/transcribe", json=request_json, timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    text = result.get("text", "").strip()
                    detected_language = result.get("detected_language", "en")
                    confidence = result.get("confidence")

                    self.logger.info(
                        f"Transcribed '{text[:50]}...' in {detected_language} (confidence: {confidence})"
                    )

                    return TranscriptionResult(
                        text=text,
                        detected_language=detected_language,
                        confidence=confidence,
                    )
                else:
                    return TranscriptionResult(
                        text=f"[Transcription error: {result.get('error', 'Unknown error')}]",
                        detected_language="en",
                        confidence=0.0,
                    )
            else:
                return TranscriptionResult(
                    text=f"[Transcription error: HTTP {response.status_code}]",
                    detected_language="en",
                    confidence=0.0,
                )

        except requests.exceptions.ConnectionError:
            return TranscriptionResult(
                text="[ASR server not available. Is the server running?]",
                detected_language="en",
                confidence=0.0,
            )
        except Exception as e:
            self.logger.error(f"Transcription error: {e}")
            return TranscriptionResult(
                text=f"[Transcription error: {str(e)}]",
                detected_language="en",
                confidence=0.0,
            )

    def transcribe(self, audio_data: np.ndarray, target_language: str = None) -> str:
        """Transcribe audio data using ASR FastAPI server (legacy interface)"""
        result = self.transcribe_with_language(audio_data, target_language)
        return result.text

    def transcribe_segments(self) -> TranscriptionResult:
        """
        Transcribe all recorded audio segments with intelligent concatenation.
        For SenseVoice Small, handles the 30-second limit by transcribing each segment separately.
        
        Returns:
            TranscriptionResult with concatenated text from all segments
        """
        with self.segment_lock:
            if not self.audio_segments:
                return TranscriptionResult(text="", detected_language="en", confidence=0.0)
            
            # Sort segments by start time
            sorted_segments = sorted(self.audio_segments, key=lambda x: x.start_time)
        
        # For SenseVoice Small with split transcription enabled
        if (self.current_asr_model == "sensevoice-small" and 
            self.svs_enable_split and 
            len(sorted_segments) > 1):
            return self._transcribe_svs_split(sorted_segments)
        
        # For other models or single segment, combine and transcribe normally
        combined_audio = self._combine_audio_segments()
        if combined_audio is None:
            return TranscriptionResult(text="", detected_language="en", confidence=0.0)
        
        return self.transcribe_with_language(combined_audio)

    def _transcribe_svs_split(self, segments: List[AudioSegment]) -> TranscriptionResult:
        """
        Transcribe multiple segments for SenseVoice Small with intelligent concatenation.
        Each segment is transcribed separately (due to 30s limit) then joined.
        """
        self.logger.info(f"[SVS] Split transcription for {len(segments)} segments")
        
        all_texts = []
        detected_langs = []
        confidences = []
        
        for i, segment in enumerate(segments):
            audio = segment.audio_data
            duration = len(audio) / self.SAMPLE_RATE
            
            # Skip if audio is too long for SVS
            if duration > 30:
                self.logger.warning(f"[SVS] Segment {i} is {duration:.1f}s, trimming to 30s")
                audio = audio[:30 * self.SAMPLE_RATE]
            
            self.logger.info(f"[SVS] Transcribing segment {i}: {len(audio)/self.SAMPLE_RATE:.1f}s")
            
            result = self.transcribe_with_language(audio)
            if result.text:
                all_texts.append(result.text)
                detected_langs.append(result.detected_language)
                if result.confidence:
                    confidences.append(result.confidence)
        
        if not all_texts:
            return TranscriptionResult(text="", detected_language="en", confidence=0.0)
        
        # Concatenate texts with intelligent joining
        combined_text = self._concatenate_transcriptions(all_texts)
        
        # Use majority vote for detected language
        detected_language = max(set(detected_langs), key=detected_langs.count)
        
        # Average confidence
        confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        self.logger.info(f"[SVS] Combined {len(all_texts)} segments into: '{combined_text[:50]}...'")
        
        return TranscriptionResult(
            text=combined_text,
            detected_language=detected_language,
            confidence=confidence
        )

    def _concatenate_transcriptions(self, texts: List[str]) -> str:
        """
        Intelligently concatenate multiple transcriptions with proper spacing and punctuation.
        """
        if not texts:
            return ""
        if len(texts) == 1:
            return texts[0].strip()
        
        result = texts[0].strip()
        
        for text in texts[1:]:
            text = text.strip()
            if not text:
                continue
            
            # Check if previous text ends with punctuation
            if result.endswith(('.', '!', '?', '。', '！', '？', ',', ';', ':')):
                result += " " + text
            else:
                result += ". " + text
        
        return result

    def get_recording_state(self) -> dict:
        """Get current recording state information"""
        with self.segment_lock:
            return {
                "is_recording": self.is_recording,
                "duration": time.time() - self.recording_start_time
                if self.is_recording
                else 0,
                "segment_count": len(self.audio_segments),
                "primary_duration": len(self.audio_buffer) * 0.1
                if self.audio_buffer
                else 0,
                "worker_count": len(self.workers),
            }

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
            self.logger.info(
                f"Switching ASR model from {self.current_asr_model} to {model_name}"
            )
            success = self.load_model(model_name)
            if success:
                self.settings_manager.set("asr_model", model_name)
                self.settings_manager.save_settings()
                # Reload model-specific settings
                self._load_model_settings()
            else:
                self.logger.error(
                    f"Failed to switch to {model_name}, keeping current model"
                )
                if self.model is None:
                    self.load_model()
