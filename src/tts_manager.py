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
        self.typing_mode = self.settings_manager.get("typing_mode", "gtt")

        # Get TTS models from ModelRegistry as single source of truth
        from src.model_registry import ModelRegistry

        self.available_tts_models = {
            model_id: model_info.display_name
            for model_id, model_info in ModelRegistry.TTS_MODELS.items()
        }

        self.current_tts_model = self.settings_manager.get("tts_model", "sopranotts")
        self.current_tts_voice = self.settings_manager.get(
            "tts_voice", "Jasper"
        )  # KittenTTS voice
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

            device = "cuda" if torch.cuda.is_available() else "cpu"
            if device == "cuda":
                print(f"🚀 Using CUDA for {model_name}")
            else:
                print(f"⚠️  CUDA not available, using CPU for {model_name}")

            # Call the FastAPI server to load the model
            response = requests.post(
                f"{TTS_SERVER_URL}/load", params={"model": model_name}, timeout=60
            )
            if response.status_code == 200:
                self.models[model_name] = True  # Mark as loaded
                print(
                    f"{self.available_tts_models.get(model_name, model_name)} model loaded successfully on {device}"
                )
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
                print(
                    f"TTS model {self.current_tts_model} not available, falling back to system TTS"
                )
                self._system_tts_fallback(text)
                return

        # Strip markdown formatting before TTS (prevent pronouncing markup)
        text = self._strip_markdown(text)

        try:
            # Build request payload based on model
            payload = {"text": text, "model": self.current_tts_model}

            # Add model-specific parameters
            if self.current_tts_model == "chatterbox-fp16":
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
            elif self.current_tts_model == "kittentts":
                # Use voice from kwargs if provided, otherwise use default
                payload["voice"] = kwargs.get("voice", self.current_tts_voice)
                payload["speed"] = kwargs.get("speed", 1.0)
                payload["clean_text"] = kwargs.get("clean_text", True)
            elif self.current_tts_model == "vibevoice":
                payload["voice"] = kwargs.get("voice", "Carter")
                payload["cfg_scale"] = kwargs.get("cfg_scale", 1.5)
                payload["temperature"] = kwargs.get("temperature", 0.9)
                payload["streaming"] = kwargs.get("streaming", False)
                payload["top_p"] = kwargs.get("top_p", 0.9)
                payload["do_sample"] = kwargs.get("do_sample", False)
                payload["streaming"] = kwargs.get("streaming", False)

            # Call the FastAPI server
            response = requests.post(
                f"{TTS_SERVER_URL}/synthesize", json=payload, timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    # Decode base64 audio
                    audio_base64 = result.get("audio_base64")
                    sample_rate = result.get("sample_rate", 24000)

                    print(
                        f"[TTS] Received audio: {len(audio_base64) if audio_base64 else 0} base64 chars, sample_rate={sample_rate}"
                    )

                    if not audio_base64:
                        print("[TTS] No audio data in response!")
                        self._system_tts_fallback(text)
                        return

                    audio_bytes = base64.b64decode(audio_base64)
                    audio_buffer = io.BytesIO(audio_bytes)

                    # Read WAV data - soundfile auto-detects format
                    audio, sr = sf.read(audio_buffer, dtype="float32")

                    print(
                        f"[TTS] Decoded audio: {len(audio)} samples, sr={sr}, dtype={audio.dtype}"
                    )

                    if len(audio) == 0:
                        print("[TTS] Empty audio array after decoding!")
                        self._system_tts_fallback(text)
                        return

                    print(
                        f"[TTS] Audio range: min={audio.min():.4f}, max={audio.max():.4f}"
                    )

                    self.play_audio(audio, sample_rate=sr)

                    # Auto-save TTS output if enabled
                    if self.settings_manager.get("tts_auto_save", True):
                        self._auto_save_tts_output(audio, sr)
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

    def _strip_markdown(self, text: str) -> str:
        """Strip markdown formatting from text before TTS"""
        import re

        # Remove code blocks
        text = re.sub(r"```[\s\S]*?```", "", text)

        # Remove inline code
        text = re.sub(r"`([^`]+)`", r"\1", text)

        # Remove headers (# ## ### etc)
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

        # Remove bold/italic markers
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"__([^_]+)__", r"\1", text)
        text = re.sub(r"_([^_]+)_", r"\1", text)

        # Remove links but keep text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        # Remove images
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)

        # Remove blockquotes
        text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)

        # Remove horizontal rules
        text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

        # Remove list markers
        text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^[\s]*\d+\.\s+", "", text, flags=re.MULTILINE)

        # Clean up extra whitespace
        text = re.sub(r"\n\s*\n", "\n", text)
        text = text.strip()

        return text

    def _system_tts_fallback(self, text: str):
        """Fallback to system TTS"""
        try:
            # Try different system TTS commands
            tts_commands = [
                ["say", text],  # macOS
                ["spd-say", "-r", "female1", text],  # Linux with speech-dispatcher
                ["espeak", "-v", "en-us", text],  # Linux with espeak
            ]

            for cmd in tts_commands:
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        return  # Success
                except (
                    subprocess.CalledProcessError,
                    subprocess.TimeoutExpired,
                    FileNotFoundError,
                ):
                    continue

            # If no system TTS works, just print
            print(f"Speaking: {text}")

        except Exception as e:
            print(f"System TTS fallback error: {e}")

    def type_text(self, text: str):
        """Type text using grus command"""
        try:
            process = subprocess.Popen(
                ["gtt", "--type", text],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                print(f"grus error: {stderr}")
                self._copy_to_clipboard(text)

        except FileNotFoundError:
            print("grus command not found. Please install grus for dictation mode.")
            self._copy_to_clipboard(text)
        except Exception as e:
            print(f"Text typing error: {e}")
            self._copy_to_clipboard(text)

    def get_window_list(self):
        """Get list of open windows using gtt --list"""
        try:
            process = subprocess.Popen(
                ["gtt", "--list"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                windows = json.loads(stdout)
                # Filter out utility windows (like XWayland bridge, GPaste)
                filtered = [
                    w
                    for w in windows
                    if w.get("wm_class") not in ["xwaylandvideobridge", "gpaste-ui"]
                    and w.get("height", 0) > 10  # Skip tiny windows
                ]
                return filtered
            else:
                print(f"gtt --list error: {stderr}")
                return []

        except FileNotFoundError:
            print("gtt command not found")
            return []
        except json.JSONDecodeError as e:
            print(f"Failed to parse gtt output: {e}")
            return []
        except Exception as e:
            print(f"Window list error: {e}")
            return []

    def focus_window(self, window_id: int):
        """Focus a window by ID using gtt --focus"""
        try:
            process = subprocess.Popen(
                ["gtt", "--focus", str(window_id)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                print(f"gtt --focus error: {stderr}")
                return False
            return True

        except FileNotFoundError:
            print("gtt command not found")
            return False
        except Exception as e:
            print(f"Window focus error: {e}")
            return False

    def focus_and_type(self, window_id: int, text: str):
        """Focus window then type text into it"""
        # First focus the window
        if self.focus_window(window_id):
            # Small delay to let window focus complete
            import time
            time.sleep(0.1)
            self.type_text(text)
        else:
            # Fallback: just try to type
            self.type_text(text)

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard as fallback"""
        try:
            clipboard_commands = [
                ["gtt", "--cb-set"],
                ["xclip", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--input"],
                ["pbcopy"],
            ]

            for cmd in clipboard_commands:
                try:
                    process = subprocess.Popen(
                        cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
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
        """Play audio data using paplay (consistent with other models)"""
        try:
            # Convert to 16-bit PCM for paplay (same as inference scripts)
            audio_int16 = (audio_data * 32767).astype(np.int16)

            print(
                f"[paplay] Playing audio: {len(audio_int16)} samples, {sample_rate}Hz, {len(audio_int16.tobytes())} bytes"
            )

            # Pipe audio to paplay
            process = subprocess.Popen(
                [
                    "paplay",
                    "--raw",
                    f"--rate={sample_rate}",
                    "--format=s16le",
                    "--channels=1",
                ],
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            process.communicate(input=audio_int16.tobytes())

            if process.returncode != 0:
                print(f"paplay error: {process.stderr.decode()}")
                # Fallback to sounddevice if paplay fails
                print("[paplay] Falling back to sounddevice...")
                sd.play(audio_data, samplerate=sample_rate)
                sd.wait()
            else:
                print("[paplay] Audio playback completed successfully")
        except FileNotFoundError:
            print("paplay not found, using sounddevice fallback")
            sd.play(audio_data, samplerate=sample_rate)
            sd.wait()
        except Exception as e:
            print(f"Audio playback error: {e}")
            # Final fallback
            try:
                sd.play(audio_data, samplerate=sample_rate)
                sd.wait()
            except:
                pass

    def get_available_tts_models(self) -> dict:
        """Get available TTS models"""
        return self.available_tts_models.copy()

    def get_current_tts_model(self) -> str:
        """Get current TTS model name"""
        return self.current_tts_model

    def set_current_tts_model(self, model_name: str):
        """Set current TTS model"""
        if model_name in self.available_tts_models:
            self.current_tts_model = model_name
            self.settings_manager.set("tts_model", model_name)
            return True
        return False

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

    def generate_speech(
        self, text: str, voice_cloning_audio: str = None, **kwargs
    ) -> np.ndarray:
        """Generate speech audio without playing it via FastAPI server"""
        if self.current_tts_model not in self.models:
            success = self.load_tts_model()
            if not success:
                print(f"TTS model {self.current_tts_model} not available")
                return np.array([])

        # Strip markdown formatting before TTS
        text = self._strip_markdown(text)

        try:
            payload = {"text": text, "model": self.current_tts_model}

            # Handle voice cloning / reference audio
            if voice_cloning_audio and voice_cloning_audio.strip():
                # Read reference audio file and encode to base64
                try:
                    with open(voice_cloning_audio, "rb") as f:
                        ref_audio_bytes = f.read()
                        ref_audio_b64 = base64.b64encode(ref_audio_bytes).decode(
                            "utf-8"
                        )
                        payload["reference_audio_base64"] = ref_audio_b64
                        # Get file extension for format detection
                        ext = Path(voice_cloning_audio).suffix.lower()
                        payload["reference_audio_format"] = ext.lstrip(".")
                except Exception as e:
                    print(f"Error reading reference audio: {e}")

            if self.current_tts_model == "chatterbox-fp16":
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
            elif self.current_tts_model == "kittentts":
                payload["voice"] = kwargs.get("voice", self.current_tts_voice)
                payload["speed"] = kwargs.get("speed", 1.0)
                payload["clean_text"] = kwargs.get("clean_text", True)

            response = requests.post(
                f"{TTS_SERVER_URL}/synthesize", json=payload, timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    audio_base64 = result.get("audio_base64")
                    audio_bytes = base64.b64decode(audio_base64)
                    audio_buffer = io.BytesIO(audio_bytes)
                    audio, sr = sf.read(audio_buffer, dtype="float32")
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

    def _auto_save_tts_output(self, audio: np.ndarray, sample_rate: int):
        """Auto-save TTS output to file with incrementing counter"""
        try:
            output_dir = Path(
                self.settings_manager.get(
                    "tts_output_dir",
                    str(Path.home() / "Documents" / "babel" / "outputs"),
                )
            )
            output_dir.mkdir(parents=True, exist_ok=True)

            counter = self.settings_manager.get("tts_output_counter", 0)
            filename = f"output_{counter:04d}.wav"
            filepath = output_dir / filename

            sf.write(filepath, audio, sample_rate)
            print(f"[TTS] Auto-saved: {filepath}")

            counter += 1
            self.settings_manager.set("tts_output_counter", counter)
            self.settings_manager.save_settings()
        except Exception as e:
            print(f"[TTS] Auto-save error: {e}")
