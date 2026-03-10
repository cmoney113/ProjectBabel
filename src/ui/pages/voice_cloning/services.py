"""
Business logic services for Voice Cloning.

This module contains service classes that encapsulate business logic
independent of Qt UI components. These services can be tested in isolation
and reused across different UI contexts.
"""

import soundfile as sf
from pathlib import Path

from .models import VoiceCloningState, GenerationResult


class AudioService:
    """Service for audio file operations.

    Handles saving and loading audio files independent of UI.
    """

    DEFAULT_SAMPLE_RATE = 24000

    def __init__(self, output_dir: Path | None = None):
        """Initialize audio service.

        Args:
            output_dir: Default output directory for saved audio
        """
        self.output_dir = output_dir

    def set_output_directory(self, output_dir: Path):
        """Set the output directory for saved audio.

        Args:
            output_dir: Output directory path
        """
        self.output_dir = output_dir

    def get_output_directory(self) -> Path:
        """Get the current output directory.

        Returns:
            Output directory path
        """
        if self.output_dir is None:
            # Default to user's documents folder
            self.output_dir = Path.home() / "Documents" / "babel" / "outputs"
        return self.output_dir

    def ensure_output_directory(self) -> Path:
        """Ensure output directory exists.

        Returns:
            Output directory path
        """
        output_dir = self.get_output_directory()
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def generate_unique_filename(
        self,
        base_name: str,
        extension: str = ".wav",
        prefix: str = "cloned_",
    ) -> str:
        """Generate a unique filename that doesn't exist.

        Args:
            base_name: Base name for the file
            extension: File extension
            prefix: Prefix for the filename

        Returns:
            Unique filename
        """
        output_dir = self.ensure_output_directory()

        counter = 0
        while True:
            filename = f"{prefix}{base_name}_{counter:04d}{extension}"
            if not (output_dir / filename).exists():
                return filename
            counter += 1

    def save_audio(
        self,
        audio_data: list[float],
        filename: str,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ) -> tuple[bool, str]:
        """Save audio data to file.

        Args:
            audio_data: Audio samples
            filename: Output filename
            sample_rate: Sample rate in Hz

        Returns:
            Tuple of (success, message)
        """
        output_dir = self.ensure_output_directory()
        file_path = output_dir / filename

        try:
            sf.write(file_path, audio_data, sample_rate)
            return True, str(file_path)
        except Exception as e:
            return False, str(e)

    def save_audio_with_unique_name(
        self,
        audio_data: list[float],
        voice_name: str,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ) -> tuple[bool, str]:
        """Save audio with a unique generated filename.

        Args:
            audio_data: Audio samples
            voice_name: Voice name to use in filename
            sample_rate: Sample rate in Hz

        Returns:
            Tuple of (success, message_or_path)
        """
        filename = self.generate_unique_filename(voice_name)
        return self.save_audio(audio_data, filename, sample_rate)


class VoiceCloningStateService:
    """Service for managing voice cloning state.

    Provides state management operations independent of UI.
    """

    def __init__(self, settings_manager):
        """Initialize state service.

        Args:
            settings_manager: Settings manager instance
        """
        self.settings_manager = settings_manager
        self.state = VoiceCloningState()

    def load_settings(self):
        """Load state from settings."""
        self.state.selected_model = self._get_model_from_settings()
        self.state.selected_voice = self.settings_manager.get("vibevoice_voice", "Carter")
        self.state.selected_language = self.settings_manager.get("tts_language", "en")

        voice_cloning = self.settings_manager.get("voice_cloning", {})
        self.state.reference_audio_path = voice_cloning.get("reference_audio_path")

    def _get_model_from_settings(self):
        """Get TTS model from settings as enum."""
        from .models import TTSModel

        model_id = self.settings_manager.get("tts_model", "vibevoice")
        try:
            return TTSModel(model_id)
        except ValueError:
            return TTSModel.VIBEVOICE

    def update_selected_voice(self, voice_name: str):
        """Update selected voice and save to settings.

        Args:
            voice_name: Selected voice name
        """
        self.state.selected_voice = voice_name
        self.settings_manager.set("vibevoice_voice", voice_name)
        self.settings_manager.save_settings()

    def update_selected_model(self, model_id: str):
        """Update selected model and save to settings.

        Args:
            model_id: Model ID string
        """
        from .models import TTSModel

        try:
            self.state.selected_model = TTSModel(model_id)
        except ValueError:
            self.state.selected_model = TTSModel.VIBEVOICE

        self.settings_manager.set("tts_model", model_id)
        self.settings_manager.save_settings()

    def update_selected_language(self, lang_code: str):
        """Update selected language and save to settings.

        Args:
            lang_code: Language code
        """
        self.state.selected_language = lang_code
        self.settings_manager.set("tts_language", lang_code)
        self.settings_manager.save_settings()

    def update_reference_audio(self, path: str):
        """Update reference audio path and save to settings.

        Args:
            path: Reference audio file path
        """
        self.state.reference_audio_path = path
        voice_cloning = self.settings_manager.get("voice_cloning", {})
        voice_cloning["reference_audio_path"] = path
        self.settings_manager.set("voice_cloning", voice_cloning)
        self.settings_manager.save_settings()

    def set_available_voices(self, voices: list[str]):
        """Update list of available voices.

        Args:
            voices: List of voice names
        """
        self.state.available_voices = voices

    def mark_generating(self, status_message: str = "Generating..."):
        """Mark state as generating.

        Args:
            status_message: Status message to display
        """
        self.state.is_generating = True
        self.state.status_message = status_message

    def mark_generation_complete(self, audio_data: list[float], sample_rate: int = 24000):
        """Mark generation as complete with audio data.

        Args:
            audio_data: Generated audio samples
            sample_rate: Audio sample rate
        """
        self.state.generated_audio = audio_data
        self.state.is_generating = False
        self.state.status_message = f"Generated {len(audio_data)} samples"

    def mark_generation_error(self, error_message: str):
        """Mark generation as failed with error.

        Args:
            error_message: Error message
        """
        self.state.is_generating = False
        self.state.status_message = f"Error: {error_message}"

    def reset_generation_state(self):
        """Reset generation-related state."""
        self.state.reset_generation_state()

    def has_generated_audio(self) -> bool:
        """Check if there is generated audio available.

        Returns:
            True if audio data exists
        """
        return self.state.generated_audio is not None and len(self.state.generated_audio) > 0

    def get_state(self) -> VoiceCloningState:
        """Get current state.

        Returns:
            Current state object
        """
        return self.state
