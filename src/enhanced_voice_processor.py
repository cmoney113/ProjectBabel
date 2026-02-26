"""
Enhanced Voice Processor with Multi-Threading Recording
Uses ASR FastAPI server for transcription
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
from typing import Optional, Callable, Any, List
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
    duration: float    # Duration in seconds
    segment_id: int
    is_primary: bool = True


class RecordingWorker(threading.Thread):
    """Worker thread for recording audio segments beyond 25.5 seconds"""
    
    SEGMENT_DURATION = 25.0  # 25 seconds per worker
    OVERLAP_DURATION = 0.5   # 0.5 second overlap for seamless joining
    
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
        self.logger.info(f"Worker {self.worker_id} started recording at {self.start_time:.3f}s")
        
        try:
            with sd.InputStream(
                samplerate=16000,
                channels=1,
                dtype='float32',
                blocksize=1600,  # 100ms chunks
                callback=self._audio_callback
            ):
                while self.is_recording and len(self.audio_buffer) < 400:  # 25 seconds at 16kHz
                    time.sleep(0.1)  # Check every 100ms
                    
                # Final processing
                if self.audio_buffer:
                    audio_data = np.concatenate(self.audio_buffer)
                    segment = AudioSegment(
                        audio_data=audio_data,
                        start_time=self.start_time,
                        duration=len(audio_data) / 16000.0,
                        segment_id=self.worker_id,
                        is_primary=False
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
    DTYPE = 'float32'
    CHUNK_SIZE = 1600  # 100ms chunks
    MAX_PRIMARY_DURATION = 25.5  # 25.5 seconds for primary buffer
    
    def __init__(self, settings_manager, waveform_widget=None):
        self.settings_manager = settings_manager
        self.waveform_widget = waveform_widget
        
        # Recording state
        self.is_recording = False
        self.recording_start_time = None
        self.audio_buffer = []  # Primary buffer (first 25.5s)
        self.stream = None
        
        # Multi-threading components
        self.workers = []  # List of RecordingWorker threads
        self.current_worker_id = 0
        self.worker_lock = threading.Lock()
        
        # Audio segments for final processing
        self.audio_segments = []
        self.segment_lock = threading.Lock()
        
        # Logging
        self.logger = logging.getLogger("EnhancedVoiceProcessor")
        
        # ASR models (same as before)
        self.available_asr_models = {
            "canary-1b-v2": "Canary 1B v2",
            "parakeet-tdt-v3": "Parakeet TDT v3"
        }
        self.current_asr_model = settings_manager.get("asr_model", "canary-1b-v2")
        self.model = None
        
    def load_model(self, model_name: str = None):
        """Load the specified ASR model via FastAPI server"""
        if model_name is None:
            model_name = self.current_asr_model
        else:
            self.current_asr_model = model_name
        
        try:
            # Call the FastAPI server to load the model
            response = requests.post(f"{ASR_SERVER_URL}/load", params={"model": model_name}, timeout=30)
            if response.status_code == 200:
                self.logger.info(f"ASR model '{model_name}' loaded successfully via FastAPI server")
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
        self.is_recording = True
        self.recording_start_time = time.time()
        self.audio_buffer = []
        self.audio_segments = []
        self.workers = []
        self.current_worker_id = 0
        
        # Start primary recording thread
        self.primary_thread = threading.Thread(target=self._primary_recording_loop, daemon=True)
        self.primary_thread.start()
        
        # Update waveform widget if available
        if self.waveform_widget:
            self.waveform_widget.set_state(self.waveform_widget.STATE_RECORDING)
        
        return True
    
    def _primary_recording_loop(self):
        """Primary recording loop for the first 25.5 seconds"""
        self.logger.info("Primary recording thread started")
        
        try:
            with sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype=self.DTYPE,
                blocksize=self.CHUNK_SIZE,
                callback=self._audio_callback
            ):
                while self.is_recording and len(self.audio_buffer) < 408:  # 25.5 seconds
                    time.sleep(0.1)  # Check every 100ms
                    
                    # Check if we need to spawn a worker
                    current_duration = len(self.audio_buffer) * 0.1  # Approximate duration
                    if current_duration >= 25.0 and not self.workers:
                        self._spawn_worker()
                
                # Primary recording complete
                if self.audio_buffer:
                    primary_audio = np.concatenate(self.audio_buffer)
                    primary_segment = AudioSegment(
                        audio_data=primary_audio,
                        start_time=self.recording_start_time,
                        duration=len(primary_audio) / self.SAMPLE_RATE,
                        segment_id=0,
                        is_primary=True
                    )
                    
                    with self.segment_lock:
                        self.audio_segments.append(primary_segment)
                    
                    self.logger.info(f"Primary recording complete: {len(primary_audio)/self.SAMPLE_RATE:.2f}s")
                    
        except Exception as e:
            self.logger.error(f"Primary recording error: {e}")
    
    def _spawn_worker(self):
        """Spawn a new worker thread for extended recording"""
        with self.worker_lock:
            self.current_worker_id += 1
            worker_start_time = time.time()
            
            worker = RecordingWorker(
                worker_id=self.current_worker_id,
                start_time=worker_start_time,
                audio_callback=self._handle_worker_segment
            )
            
            self.workers.append(worker)
            worker.start()
            
            self.logger.info(f"Spawned worker {self.current_worker_id} at {worker_start_time:.3f}s")
    
    def _handle_worker_segment(self, segment: AudioSegment):
        """Handle completed audio segment from worker thread"""
        with self.segment_lock:
            self.audio_segments.append(segment)
            self.logger.info(f"Received segment {segment.segment_id}: {segment.duration:.2f}s")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Audio callback for primary recording"""
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
        if hasattr(self, 'primary_thread'):
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
                prev_end_time = sorted_segments[i-1].start_time + sorted_segments[i-1].duration
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
                        self.logger.debug(f"Trimmed {overlap_samples} samples from segment {i}")
                    else:
                        # Entire segment is overlap, skip it
                        self.logger.warning(f"Segment {i} is entirely overlap, skipping")
                else:
                    # No significant overlap, just append
                    combined_audio = np.concatenate([combined_audio, segment.audio_data])
            
            total_duration = len(combined_audio) / self.SAMPLE_RATE
            self.logger.info(f"Combined audio duration: {total_duration:.2f}s")
            
            return combined_audio
    
    def transcribe(self, audio_data: np.ndarray, target_language: str = None) -> str:
        """Transcribe audio data using ASR FastAPI server
        
        Args:
            audio_data: Audio numpy array
            target_language: Target language for translation (if None, uses settings)
        
        Note: For languages NOT supported by Qwen-TTS, translation is handled by LLM instead.
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
            sf.write(buffer, audio_data, self.SAMPLE_RATE, format='WAV')
            buffer.seek(0)
            audio_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            
            # Get source language from settings
            source_language = self.settings_manager.get("target_language", "en")
            
            # Build request - ASR always transcribes in detected/source language
            # LLM translation happens separately in main.py if needed
            request_json = {
                "audio_data": audio_base64,
                "model": self.current_asr_model,
                "sample_rate": self.SAMPLE_RATE,
                "language": source_language,
            }
            
            # Call the FastAPI server (no translation - done by LLM)
            response = requests.post(
                f"{ASR_SERVER_URL}/transcribe",
                json=request_json,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    text = result.get("text", "").strip()
                    
                    # If we didn't use ASR translation but target is set, 
                    # we need LLM translation - this is handled in main.py
                    return text
                else:
                    return f"[Transcription error: {result.get('error', 'Unknown error')}]"
            else:
                return f"[Transcription error: HTTP {response.status_code}]"
                
        except requests.exceptions.ConnectionError:
            return "[ASR server not available. Is the server running?]"
        except Exception as e:
            self.logger.error(f"Transcription error: {e}")
            return f"[Transcription error: {str(e)}]"
    
    def get_recording_state(self) -> dict:
        """Get current recording state information"""
        with self.segment_lock:
            return {
                'is_recording': self.is_recording,
                'duration': time.time() - self.recording_start_time if self.is_recording else 0,
                'segment_count': len(self.audio_segments),
                'primary_duration': len(self.audio_buffer) * 0.1 if self.audio_buffer else 0,
                'worker_count': len(self.workers)
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
            self.logger.info(f"Switching ASR model from {self.current_asr_model} to {model_name}")
            success = self.load_model(model_name)
            if success:
                self.settings_manager.set("asr_model", model_name)
                self.settings_manager.save_settings()
            else:
                self.logger.error(f"Failed to switch to {model_name}, keeping current model")
                if self.model is None:
                    self.load_model()