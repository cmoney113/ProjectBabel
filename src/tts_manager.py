"""
TTS Manager for Canary Voice AI Assistant
Handles text-to-speech using multiple TTS models and text output via gtt
Uses TTS FastAPI server for lazy loading
"""

import subprocess
import json
import os
import tempfile
import sounddevice as sd
import numpy as np
import base64
import io
import soundfile as sf
import requests
from pathlib import Path
from typing import Optional, Dict, Any

# TTS Server configuration
TTS_SERVER_URL = "http://localhost:8711"


class TTSManager:
    """Manages TTS functionality with multiple TTS models and gtt integration"""
    
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.typing_mode = self.settings_manager.get("typing_mode", "wbind")
        
        # Available TTS models (removed chatterbox-turbo)
        self.available_tts_models = {
            "neutts-nano": "NeuTTS-Nano",
            "chatterbox-fp16": "Chatterbox FP16 (Multilingual)",
            "sopranotts": "SopranoTTS",
            "qwen-tts": "Qwen-TTS (0.6B CustomVoice)"
        }
        
        self.current_tts_model = self.settings_manager.get("tts_model", "neutts-nano")
        self.models = {}  # Cache loaded models - don't load automatically
        
    def load_tts_model(self, model_name: str = None):
        """Load the specified TTS model via FastAPI server"""
        if model_name is None:
            model_name = self.current_tts_model
        else:
            self.current_tts_model = model_name
            
        if model_name in self.models:
            return True  # Already loaded
        
        try:
            # Check CUDA availability
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            if device == 'cuda':
                print(f"🚀 Using CUDA for {model_name}")
            else:
                print(f"⚠️  CUDA not available, using CPU for {model_name}")
            
            # Call the FastAPI server to load the model
            response = requests.post(f"{TTS_SERVER_URL}/load", params={"model": model_name}, timeout=60)
            if response.status_code == 200:
                self.models[model_name] = True  # Mark as loaded
                print(f"{self.available_tts_models.get(model_name, model_name)} model loaded successfully on {device}")
                return True
            else:
                print(f"Error loading TTS model: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"Cannot connect to TTS server. Is it running?")
            return False
        except Exception as e:
            print(f"Error loading {model_name} model: {e}")
            return False
            
    def speak(self, text: str, voice_cloning_audio: str = None, **kwargs):
        """Speak text using current TTS model via FastAPI server"""
        # Ensure model is loaded
        if self.current_tts_model not in self.models:
            success = self.load_tts_model()
            if not success:
                print(f"TTS model {self.current_tts_model} not available, falling back to system TTS")
                self._system_tts_fallback(text)
                return
        
        try:
            # Build request payload based on model
            payload = {
                "text": text,
                "model": self.current_tts_model
            }
            
            # Add model-specific parameters
            if self.current_tts_model == "neutts-nano":
                payload["voice_id"] = kwargs.get("voice_id", "default")
                payload["speed"] = kwargs.get("speed", 1.0)
                payload["pitch"] = kwargs.get("pitch", 1.0)
            elif self.current_tts_model == "chatterbox-fp16":
                payload["language"] = kwargs.get("language", "en")
                payload["exaggeration"] = kwargs.get("exaggeration", 0.3)
                payload["cfg_weight"] = kwargs.get("cfg_weight", 0.1)
                payload["temperature"] = kwargs.get("temperature", 0.8)
            elif self.current_tts_model == "sopranotts":
                payload["temperature"] = kwargs.get("temperature", 0.3)
                payload["top_p"] = kwargs.get("top_p", 0.95)
                payload["repetition_penalty"] = kwargs.get("repetition_penalty", 1.2)
            elif self.current_tts_model == "qwen-tts":
                payload["speaker"] = kwargs.get("speaker", "Vivian")
                payload["language"] = kwargs.get("language", "Chinese")
                payload["instruction"] = kwargs.get("instruction", None)
                payload["non_streaming_mode"] = kwargs.get("non_streaming_mode", True)
            
            # Call the FastAPI server
            response = requests.post(f"{TTS_SERVER_URL}/synthesize", json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    # Decode base64 audio
                    audio_base64 = result.get("audio_base64")
                    sample_rate = result.get("sample_rate", 24000)
                    
                    audio_bytes = base64.b64decode(audio_base64)
                    audio_buffer = io.BytesIO(audio_bytes)
                    audio, sr = sf.read(audio_buffer, dtype='float32')
                    
                    self.play_audio(audio, sample_rate=sample_rate)
                else:
                    print(f"TTS synthesis error: {result.get('error')}")
                    self._system_tts_fallback(text)
            else:
                print(f"TTS HTTP error: {response.status_code}")
                self._system_tts_fallback(text)
                
        except requests.exceptions.ConnectionError:
            print("Cannot connect to TTS server. Is it running?")
            self._system_tts_fallback(text)
        except Exception as e:
            print(f"TTS error: {e}")
            self._system_tts_fallback(text)
            
    def _system_tts_fallback(self, text: str):
        """Fallback to system TTS"""
        try:
            # Try different system TTS commands
            tts_commands = [
                ["say", text],  # macOS
                ["spd-say", "-r", "female1", text],  # Linux with speech-dispatcher
                ["espeak", "-v", "en-us", text]  # Linux with espeak
            ]
            
            for cmd in tts_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        return  # Success
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                    continue
                    
            # If no system TTS works, just print
            print(f"Speaking: {text}")
            
        except Exception as e:
            print(f"System TTS fallback error: {e}")
            
    def type_text(self, text: str):
        """Type text using gtt command"""
        try:
            process = subprocess.Popen(
                ["wbind", "--type", text],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"wbind error: {stderr}")
                self._copy_to_clipboard(text)
                
        except FileNotFoundError:
            print("wbind command not found. Please install gtt for dictation mode.")
            self._copy_to_clipboard(text)
        except Exception as e:
            print(f"Text typing error: {e}")
            self._copy_to_clipboard(text)
            
    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard as fallback"""
        try:
            clipboard_commands = [
                ["wl-copy"],
                ["xclip", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--input"],
                ["pbcopy"],
            ]
            
            for cmd in clipboard_commands:
                try:
                    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    process.communicate(input=text)
                    if process.returncode == 0:
                        print("Text copied to clipboard")
                        return
                except (FileNotFoundError, subprocess.SubprocessError):
                    continue
                    
            print(f"Clipboard copy failed. Text: {text[:100]}...")
            
        except Exception as e:
            print(f"Clipboard error: {e}")
            
    def play_audio(self, audio_data: np.ndarray, sample_rate: int = 24000):
        """Play audio data using sounddevice"""
        try:
            sd.play(audio_data, samplerate=sample_rate)
            sd.wait()
        except Exception as e:
            print(f"Audio playback error: {e}")
            
    def get_available_tts_models(self) -> dict:
        """Get available TTS models"""
        return self.available_tts_models.copy()
        
    def get_current_tts_model(self) -> str:
        """Get current TTS model name"""
        return self.current_tts_model
        
    def switch_tts_model(self, model_name: str):
        """Switch to a different TTS model"""
        if model_name not in self.available_tts_models:
            raise ValueError(f"Unknown TTS model: {model_name}")
            
        if model_name != self.current_tts_model:
            print(f"Switching TTS model from {self.current_tts_model} to {model_name}")
            success = self.load_tts_model(model_name)
            if success:
                self.settings_manager.set("tts_model", model_name)
                self.settings_manager.save_settings()
            else:
                print(f"Failed to switch to {model_name}, keeping current model")
                if model_name not in self.models:
                    self.load_tts_model()
            
    def generate_speech(self, text: str, voice_cloning_audio: str = None, **kwargs) -> np.ndarray:
        """Generate speech audio without playing it via FastAPI server"""
        if self.current_tts_model not in self.models:
            success = self.load_tts_model()
            if not success:
                print(f"TTS model {self.current_tts_model} not available")
                return np.array([])
        
        try:
            payload = {
                "text": text,
                "model": self.current_tts_model
            }
            
            if self.current_tts_model == "neutts-nano":
                payload["voice_id"] = kwargs.get("voice_id", "default")
                payload["speed"] = kwargs.get("speed", 1.0)
                payload["pitch"] = kwargs.get("pitch", 1.0)
            elif self.current_tts_model == "chatterbox-fp16":
                payload["language"] = kwargs.get("language", "en")
                payload["exaggeration"] = kwargs.get("exaggeration", 0.3)
                payload["cfg_weight"] = kwargs.get("cfg_weight", 0.1)
                payload["temperature"] = kwargs.get("temperature", 0.8)
            elif self.current_tts_model == "sopranotts":
                payload["temperature"] = kwargs.get("temperature", 0.3)
                payload["top_p"] = kwargs.get("top_p", 0.95)
                payload["repetition_penalty"] = kwargs.get("repetition_penalty", 1.2)
            elif self.current_tts_model == "qwen-tts":
                payload["speaker"] = kwargs.get("speaker", "Vivian")
                payload["language"] = kwargs.get("language", "Chinese")
                payload["instruction"] = kwargs.get("instruction", None)
            
            response = requests.post(f"{TTS_SERVER_URL}/synthesize", json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    audio_base64 = result.get("audio_base64")
                    audio_bytes = base64.b64decode(audio_base64)
                    audio_buffer = io.BytesIO(audio_bytes)
                    audio, sr = sf.read(audio_buffer, dtype='float32')
                    return audio
                else:
                    print(f"TTS synthesis error: {result.get('error')}")
                    return np.array([])
            else:
                print(f"TTS HTTP error: {response.status_code}")
                return np.array([])
                
        except requests.exceptions.ConnectionError:
            print("Cannot connect to TTS server. Is it running?")
            return np.array([])
        except Exception as e:
            print(f"TTS error: {e}")
            return np.array([])
