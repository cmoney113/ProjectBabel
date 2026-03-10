"""
Signal/slot handlers for Voice Cloning page.

This module contains handler classes that encapsulate the business logic
for responding to user interactions. Handlers are separated from widgets
for better testability and to maintain clear separation of concerns.
"""

import shutil
from pathlib import Path

from PySide6.QtWidgets import QFileDialog
from qfluentwidgets import InfoBar

from .models import TTSModel, VoicePreset
from .worker import VoiceCloneWorker


class VoiceManagementHandler:
    """Handler for voice preset management operations.

    Handles importing, deleting, and refreshing voice presets.
    Interacts with file system and displays user feedback.
    """

    # Protected voices that cannot be deleted
    PROTECTED_VOICES = frozenset(["Carter", "Emma", "Davis", "Frank", "Grace", "Mike"])

    def __init__(self, voices_dir: Path, settings_manager, widget):
        """Initialize handler.

        Args:
            voices_dir: Directory containing voice preset files
            settings_manager: Settings manager instance
            widget: Parent widget for InfoBar display
        """
        self.voices_dir = voices_dir
        self.settings_manager = settings_manager
        self.widget = widget

    def ensure_voices_directory(self) -> bool:
        """Ensure voices directory exists, try alternative paths if needed.

        Returns:
            True if directory exists or was created, False otherwise
        """
        if self.voices_dir.exists():
            return True

        # Try alternative path
        alt_path = self.voices_dir.parent / "voices"
        if alt_path.exists():
            self.voices_dir = alt_path
            return True

        return False

    def get_available_voices(self) -> list[str]:
        """Get list of available voice preset names.

        Returns:
            Sorted list of voice names
        """
        if not self.voices_dir.exists():
            return []

        voice_files = []
        for pt_path in self.voices_dir.rglob("*.pt"):
            voice_files.append(pt_path.stem)

        return sorted(voice_files)

    def import_voice(self, file_path: str) -> tuple[bool, str]:
        """Import a voice preset file.

        Args:
            file_path: Path to the .pt voice file

        Returns:
            Tuple of (success, message)
        """
        if not file_path:
            return False, "No file selected"

        source = Path(file_path)
        voice_name = source.stem

        # Check if voice already exists
        dest_path = self.voices_dir / f"{voice_name}.pt"
        if dest_path.exists():
            return False, f"Voice '{voice_name}' already exists"

        # Create directory if needed
        try:
            self.voices_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"Failed to create directory: {str(e)}"

        # Copy file
        try:
            shutil.copy2(source, dest_path)
            return True, f"Successfully imported '{voice_name}'"
        except Exception as e:
            return False, f"Failed to import voice: {str(e)}"

    def delete_voice(self, voice_name: str) -> tuple[bool, str]:
        """Delete a voice preset.

        Args:
            voice_name: Name of the voice to delete

        Returns:
            Tuple of (success, message)
        """
        if not voice_name:
            return False, "No voice selected"

        # Don't allow deleting built-in voices
        if voice_name in self.PROTECTED_VOICES:
            return False, f"Cannot delete built-in voice '{voice_name}'"

        # Find and delete the file
        for pt_path in self.voices_dir.rglob(f"{voice_name}.pt"):
            try:
                pt_path.unlink()
                return True, f"Successfully deleted '{voice_name}'"
            except Exception as e:
                return False, f"Failed to delete voice: {str(e)}"

        return False, f"Voice file not found for '{voice_name}'"

    def is_protected_voice(self, voice_name: str) -> bool:
        """Check if a voice is protected from deletion.

        Args:
            voice_name: Name of the voice

        Returns:
            True if voice is protected
        """
        return voice_name in self.PROTECTED_VOICES

    def show_info_bar(self, level: str, title: str, message: str, duration: int = 2000):
        """Display an InfoBar notification.

        Args:
            level: 'success', 'warning', or 'error'
            title: InfoBar title
            message: InfoBar message
            duration: Display duration in milliseconds
        """
        info_bar_method = getattr(InfoBar, level)
        info_bar_method(title, message, parent=self.widget, duration=duration)


class ReferenceAudioHandler:
    """Handler for reference audio operations.

    Handles browsing for and managing reference audio files.
    """

    AUDIO_FILTER = "Audio Files (*.wav *.mp3 *.flac *.ogg);;All Files (*)"

    def __init__(self, settings_manager):
        """Initialize handler.

        Args:
            settings_manager: Settings manager instance
        """
        self.settings_manager = settings_manager

    def browse_reference_audio(self, parent_widget) -> str | None:
        """Open file dialog to select reference audio.

        Args:
            parent_widget: Parent widget for file dialog

        Returns:
            Selected file path or None
        """
        file_path, _ = QFileDialog.getOpenFileName(
            parent_widget,
            "Select Reference Audio",
            str(Path.home()),
            self.AUDIO_FILTER,
        )
        return file_path if file_path else None

    def save_reference_audio_path(self, path: str):
        """Save reference audio path to settings.

        Args:
            path: Path to reference audio file
        """
        voice_cloning = self.settings_manager.get("voice_cloning", {})
        voice_cloning["reference_audio_path"] = path
        self.settings_manager.set("voice_cloning", voice_cloning)
        self.settings_manager.save_settings()

    def get_saved_reference_audio_path(self) -> str:
        """Get saved reference audio path from settings.

        Returns:
            Saved path or empty string
        """
        voice_cloning = self.settings_manager.get("voice_cloning", {})
        return voice_cloning.get("reference_audio_path", "")


class GenerationHandler:
    """Handler for voice generation operations.

    Manages the generation workflow including starting workers
    and handling results.
    """

    def __init__(self, tts_manager, settings_manager):
        """Initialize handler.

        Args:
            tts_manager: TTS manager instance
            settings_manager: Settings manager instance
        """
        self.tts_manager = tts_manager
        self.settings_manager = settings_manager
        self._worker: VoiceCloneWorker | None = None

    def start_generation(
        self,
        text: str,
        model: TTSModel | str,
        voice_name: str | None = None,
        reference_audio_path: str | None = None,
    ) -> VoiceCloneWorker:
        """Start voice generation in background thread.

        Args:
            text: Text to synthesize
            model: TTS model ID
            voice_name: Voice preset name (for VibeVoice)
            reference_audio_path: Reference audio path (for Chatterbox)

        Returns:
            The worker thread instance
        """
        model_id = model.value if isinstance(model, TTSModel) else model

        self._worker = VoiceCloneWorker(
            self.tts_manager,
            text,
            model_id,
            voice_name=voice_name,
            reference_audio_path=reference_audio_path,
        )

        return self._worker

    def get_worker(self) -> VoiceCloneWorker | None:
        """Get the current worker instance.

        Returns:
            Current worker or None
        """
        return self._worker

    def validate_generation_request(
        self,
        text: str,
        model: TTSModel | str,
        voice_name: str | None,
        reference_audio_path: str | None,
    ) -> tuple[bool, str]:
        """Validate generation request parameters.

        Args:
            text: Text to synthesize
            model: TTS model ID
            voice_name: Voice preset name
            reference_audio_path: Reference audio path

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text or not text.strip():
            return False, "Please enter text to synthesize"

        model_id = model.value if isinstance(model, TTSModel) else model

        if model_id == "vibevoice":
            if not voice_name:
                return False, "Please select a voice preset"
        else:
            if not reference_audio_path:
                return False, "Please select a reference audio file"
            if not Path(reference_audio_path).exists():
                return False, "Reference audio file not found"

        return True, ""
