"""
Settings Manager for Canary Voice AI Assistant
Handles loading and managing application settings from settings.json
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class SettingsManager:
    """Manages application settings and configuration"""

    def __init__(self, settings_path: str = "./settings.json"):
        self.settings_path = Path(settings_path)
        self.settings = self.load_settings()

    def load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file"""
        if not self.settings_path.exists():
            # Create default settings if file doesn't exist
            return self.create_default_settings()

        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
            return self.create_default_settings()

    def create_default_settings(self) -> Dict[str, Any]:
        """Create default settings"""
        default_settings = {
            "groq_api_key": "",
            "groq_model": "openai/gpt-oss-120b",
            "groq_api_endpoint": "https://api.groq.com/openai/v1/chat/completions",
            "post_process_prompt": "You are a DICTATION POST-PROCESSOR - NOT a conversational assistant...",
            "voice_ai_prompt": "You are a helpful assistant.",
            "silence_timeout_ms": 1000,
            "asr_model": "canary-1b-v2",
            "tts_model": "neutts-nano",
            "enable_vad": True,
            "enable_llm": True,
            "paste_output": False,
            "min_words_for_llm": 7,
            "typing_mode": "wbind",
            "target_language": "english",
            "tts_streaming": False,
            # Auto-save TTS outputs
            "tts_auto_save": True,
            "tts_output_dir": str(Path.home() / "Documents" / "babel" / "outputs"),
            "tts_output_counter": 0,
            "tavily_api_key": "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",
            "hotkey": "Ctrl+Space",
            "auto_vad_trigger": True,
            "dictation_mode": False,
            # ASR Model Settings
            "asr_settings": {
                "canary-1b-v2": {"provider": "CPUExecutionProvider", "language": "en"},
                "parakeet-tdt-v3": {
                    "silence_threshold": 0.001,
                    "min_audio_length": 1.0,
                    "max_audio_length": 5.0,
                },
            },
            # TTS Model Settings
            "tts_settings": {
                "neutts-nano": {"voice_id": "default", "speed": 1.0, "pitch": 1.0},
                "chatterbox-fp16": {
                    "language": "en",
                    "exaggeration": 0.3,
                    "cfg_weight": 0.1,
                    "temperature": 0.8,
                    "repetition_penalty": 1.2,
                },
                "chatterbox-turbo": {
                    "max_new_tokens": 1024,
                    "repetition_penalty": 1.2,
                    "apply_watermark": False,
                },
            },
            # Voice Cloning Settings
            "voice_cloning": {
                "reference_audio_path": "",
                "save_cloned_voices": True,
                "cloned_voices_dir": "./cloned_voices",
            },
            "rules": [],
            "profiles": {},
        }
        return default_settings

    def get(self, key: str, default: Any = None) -> Any:
        """Get setting value by key"""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        """Set setting value"""
        self.settings[key] = value

    def save_settings(self):
        """Save settings to JSON file"""
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get_groq_config(self) -> Dict[str, str]:
        """Get Groq API configuration"""
        return {
            "api_key": self.get("groq_api_key", ""),
            "model": self.get("groq_model", "openai/gpt-oss-120b"),
            "endpoint": self.get(
                "groq_api_endpoint", "https://api.groq.com/openai/v1/chat/completions"
            ),
        }

    def get_tavily_config(self) -> Dict[str, str]:
        """Get Tavily API configuration"""
        return {
            "api_key": self.get(
                "tavily_api_key", "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"
            )
        }

    def get_voice_ai_prompt(self) -> str:
        """Get voice AI prompt template"""
        return self.get("voice_ai_prompt", "You are a helpful assistant.")

    def get_post_process_prompt(self) -> str:
        """Get post-processing prompt template"""
        return self.get("post_process_prompt", "You are a DICTATION POST-PROCESSOR...")
