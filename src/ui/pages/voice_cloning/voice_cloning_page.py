"""
Voice Cloning Page - Main coordinator module.

This module provides the VoiceCloningPage widget which coordinates
all sub-components for the voice cloning feature.

Architecture:
    - VoiceCloningPage: Main coordinator (<150 LOC)
    - widgets.py: Self-contained UI sub-components
    - handlers.py: Signal/slot business logic handlers
    - services.py: Business logic services (Qt-agnostic)
    - worker.py: Background thread workers
    - models.py: Data models and enums

Signal Flow:
    User Action -> Widget Signal -> Handler -> Service -> Worker -> Signal -> UI Update
"""

from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import SubtitleLabel, InfoBar

from .models import TTSModel
from .widgets import (
    ModelSelectionCard,
    VibeVoiceSelectionCard,
    ChatterboxReferenceCard,
    TextInputCard,
    GenerationControlsCard,
)
from .handlers import VoiceManagementHandler, ReferenceAudioHandler, GenerationHandler
from .services import AudioService, VoiceCloningStateService
from .worker import VoiceCloneWorker


class VoiceCloningPage(QWidget):
    """Voice cloning page coordinator.

    Coordinates sub-widgets and handlers for voice cloning functionality.
    Keeps business logic in handlers/services, UI in widgets.

    Public Methods:
        get_tts_model_combo(): For external styling
        get_generate_button(): For external styling
        get_vibevoice_voice(): Get selected voice name
        get_reference_audio_path(): Get reference audio path
    """

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        # Get references to managers
        self.settings_manager = main_window.get_settings_manager()
        self.tts_manager = main_window.get_tts_manager()

        # Initialize state
        self.cloned_audio_data = None
        self.cloned_audio_sample_rate = 24000
        self.current_voice_file = None

        # Initialize services
        self.state_service = VoiceCloningStateService(self.settings_manager)
        self.audio_service = AudioService()
        self.state_service.load_settings()

        # Initialize handlers
        self.voice_handler = VoiceManagementHandler(
            self._get_voices_directory(),
            self.settings_manager,
            self,
        )
        self.ref_audio_handler = ReferenceAudioHandler(self.settings_manager)
        self.generation_handler = GenerationHandler(self.tts_manager, self.settings_manager)

        # Initialize UI
        self._init_ui()
        self._connect_signals()
        self._refresh_voice_list()

        # Restore saved state
        self._restore_state()

    def _get_voices_directory(self) -> Path:
        """Get VibeVoice voices directory."""
        return (
            Path.home()
            / "new-projects"
            / "voice_ai"
            / "models"
            / "VibeVoiceRealtime05b"
            / "voices"
            / "streaming_model"
        )

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.setObjectName("voice_cloning_page")

        # Header
        header_layout = QHBoxLayout()
        title = SubtitleLabel("Voice Cloning")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Sub-widgets
        self.model_card = ModelSelectionCard()
        self.voice_card = VibeVoiceSelectionCard()
        self.reference_card = ChatterboxReferenceCard()
        self.text_card = TextInputCard()
        self.controls_card = GenerationControlsCard()

        # Add to layout
        layout.addWidget(self.model_card)
        layout.addWidget(self.voice_card)
        layout.addWidget(self.reference_card)
        layout.addWidget(self.text_card)
        layout.addWidget(self.controls_card)

        layout.addStretch()

    def _connect_signals(self):
        """Connect all widget signals to handlers."""
        # Model selection
        self.model_card.model_changed.connect(self._on_model_changed)

        # Voice management
        self.voice_card.voice_selected.connect(self._on_voice_selected)
        self.voice_card.import_requested.connect(self._on_import_voice)
        self.voice_card.delete_requested.connect(self._on_delete_voice)
        self.voice_card.refresh_requested.connect(self._refresh_voice_list)

        # Reference audio
        self.reference_card.browse_requested.connect(self._on_browse_reference_audio)

        # Text input
        self.text_card.language_changed.connect(self._on_language_changed)

        # Generation controls
        self.controls_card.generate_requested.connect(self._on_generate)
        self.controls_card.play_requested.connect(self._on_play)
        self.controls_card.save_requested.connect(self._on_save)

    def _restore_state(self):
        """Restore UI state from settings."""
        # Model selection
        current_model = self.settings_manager.get("tts_model", "vibevoice")
        self.model_card.set_current_model(current_model)
        self._update_model_visibility(current_model)

        # Language
        current_lang = self.settings_manager.get("tts_language", "en")
        self.text_card.set_language_code(current_lang)

        # Reference audio
        saved_ref_audio = self.ref_audio_handler.get_saved_reference_audio_path()
        if saved_ref_audio:
            self.reference_card.set_reference_audio_path(saved_ref_audio)

    def _update_model_visibility(self, model_id: str):
        """Update card visibility based on selected model."""
        is_vibevoice = model_id == "vibevoice"
        self.voice_card.setVisible(is_vibevoice)
        self.reference_card.setVisible(not is_vibevoice)
        self.model_card.update_description(model_id)

    def _refresh_voice_list(self):
        """Refresh the list of available voices."""
        self.voice_card.clear_voices()

        if not self.voice_handler.ensure_voices_directory():
            self.voice_card.show_not_found_message(
                Path.home()
                / "new-projects"
                / "voice_ai"
                / "models"
                / "VibeVoiceRealtime05b"
                / "voices"
            )
            return

        voices = self.voice_handler.get_available_voices()
        self.state_service.set_available_voices(voices)

        for voice in voices:
            self.voice_card.add_voice(voice)

        self.voice_card.set_voice_count(len(voices))

        # Select default voice
        if voices:
            default_voice = self.settings_manager.get("vibevoice_voice", "Carter")
            if not self.voice_card.find_and_select_voice(default_voice):
                self.voice_card.select_first_voice()

    # ========== Event Handlers ==========

    def _on_model_changed(self, model_id: str):
        """Handle model selection change."""
        self._update_model_visibility(model_id)
        self.state_service.update_selected_model(model_id)

    def _on_voice_selected(self, voice_name: str):
        """Handle voice selection."""
        self.state_service.update_selected_voice(voice_name)
        self.voice_card.set_selected_voice_display(voice_name)

    def _on_import_voice(self):
        """Handle voice import request."""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Voice File",
            str(Path.home()),
            "Voice Files (*.pt);;All Files (*)",
        )

        if file_path:
            success, message = self.voice_handler.import_voice(file_path)
            level = "success" if success else "error"
            self.voice_handler.show_info_bar(level, "Voice Imported" if success else "Import Failed", message, 2000 if success else 3000)

            if success:
                self._refresh_voice_list()

    def _on_delete_voice(self):
        """Handle voice delete request."""
        voice_name = self.voice_card.get_selected_voice()

        if not voice_name:
            self.voice_handler.show_info_bar("warning", "No Selection", "Please select a voice to delete", 2000)
            return

        success, message = self.voice_handler.delete_voice(voice_name)
        level = "success" if success else "error"
        self.voice_handler.show_info_bar(level, "Voice Deleted" if success else "Delete Failed", message, 2000 if success else 3000)

        if success:
            self._refresh_voice_list()

    def _on_browse_reference_audio(self):
        """Handle browse reference audio request."""
        file_path = self.ref_audio_handler.browse_reference_audio(self)

        if file_path:
            self.reference_card.set_reference_audio_path(file_path)
            self.state_service.update_reference_audio(file_path)

    def _on_language_changed(self, lang_code: str):
        """Handle language selection change."""
        self.state_service.update_selected_language(lang_code)

    def _on_generate(self):
        """Handle generate button click."""
        text = self.text_card.get_text()
        model = self.model_card.get_current_model()
        voice_name = self.voice_card.get_selected_voice()
        ref_audio = self.reference_card.get_reference_audio_path()

        # Validate
        is_valid, error_msg = self.generation_handler.validate_generation_request(
            text, model, voice_name, ref_audio
        )

        if not is_valid:
            self.voice_handler.show_info_bar("warning", "Validation Error", error_msg, 2000)
            return

        # Update UI for generating state
        self.controls_card.set_generating_state(True)
        self.controls_card.set_status(f"Generating with {model}...")
        self.state_service.mark_generating(f"Generating with {model}...")

        # Start worker
        worker = self.generation_handler.start_generation(
            text=text,
            model=model,
            voice_name=voice_name if model == "vibevoice" else None,
            reference_audio_path=ref_audio if model != "vibevoice" else None,
        )

        worker.progress.connect(self.controls_card.set_status)
        worker.finished.connect(self._on_generation_complete)
        worker.error.connect(self._on_generation_error)
        worker.start()

    def _on_generation_complete(self, audio_data):
        """Handle generation complete."""
        self.cloned_audio_data = audio_data
        self.cloned_audio_sample_rate = 24000

        self.controls_card.set_ready_state(has_audio=True)
        self.controls_card.set_status(f"Generated {len(audio_data)} samples")
        self.state_service.mark_generation_complete(audio_data, self.cloned_audio_sample_rate)

        self.voice_handler.show_info_bar("success", "Generation Complete", "Voice cloned successfully", 2000)

    def _on_generation_error(self, error_message: str):
        """Handle generation error."""
        self.controls_card.set_generating_state(False)
        self.controls_card.set_status(f"Error: {error_message}")
        self.state_service.mark_generation_error(error_message)

        self.voice_handler.show_info_bar("error", "Generation Failed", error_message, 3000)

    def _on_play(self):
        """Handle play button click."""
        if self.state_service.has_generated_audio():
            self.controls_card.set_status("Playing...")
            self.tts_manager.play_audio(
                self.state_service.get_state().generated_audio,
                self.cloned_audio_sample_rate,
            )
            self.controls_card.set_status("Playback complete")
        else:
            self.voice_handler.show_info_bar("warning", "No Audio", "No audio to play. Generate first.", 2000)

    def _on_save(self):
        """Handle save button click."""
        state = self.state_service.get_state()

        if not state.generated_audio or len(state.generated_audio) == 0:
            self.voice_handler.show_info_bar("warning", "No Audio", "No audio to save. Generate first.", 2000)
            return

        voice_name = self.voice_card.get_selected_voice() or "cloned"
        success, result = self.audio_service.save_audio_with_unique_name(
            state.generated_audio,
            voice_name,
            self.cloned_audio_sample_rate,
        )

        if success:
            file_path = Path(result)
            self.voice_handler.show_info_bar("success", "Audio Saved", f"Saved to {file_path.name}", 2000)
        else:
            self.voice_handler.show_info_bar("error", "Save Failed", result, 3000)

    # ========== Public Methods for MainWindow compatibility ==========

    def get_tts_model_combo(self):
        """Get TTS model combo for styling."""
        return self.model_card.model_combo

    def get_generate_button(self):
        """Get generate button for styling."""
        return self.controls_card.generate_btn

    def get_vibevoice_voice(self):
        """Get selected VibeVoice voice name."""
        return self.voice_card.get_selected_voice() or self.settings_manager.get("vibevoice_voice", "Carter")

    def get_reference_audio_path(self):
        """Get reference audio path for Chatterbox."""
        return self.reference_card.get_reference_audio_path()
