"""
Reusable widget components for Voice Cloning page.

This module contains self-contained QWidget subclasses that encapsulate
specific UI features. Each widget manages its own internal layout and
emits signals for parent coordination.
"""

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
)
from qfluentwidgets import (
    SubtitleLabel,
    BodyLabel,
    PushButton,
    ComboBox,
    LineEdit,
    TextEdit,
    CardWidget,
    SpinBox,
    InfoBar,
    PrimaryPushButton,
    ListWidget,
    IndeterminateProgressRing,
)

from .models import TTSModel, Language


class ModelSelectionCard(CardWidget):
    """Card widget for TTS model selection.

    Signals:
        model_changed: Emitted when user selects a different model
    """

    model_changed = Signal(str)  # model_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        self.model_title = SubtitleLabel("TTS Model")
        self.model_title.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: white;"
        )
        layout.addWidget(self.model_title)

        # Model selection
        model_select_layout = QHBoxLayout()
        model_select_layout.addWidget(BodyLabel("Model:"))

        self.model_combo = ComboBox()

        # Dynamically populate models that support voice cloning from ModelRegistry
        from src.model_registry import ModelRegistry

        for model_id, model_info in ModelRegistry.TTS_MODELS.items():
            if model_info.voice_cloning_type is not None:
                self.model_combo.addItem(model_info.display_name, userData=model_id)

        model_select_layout.addWidget(self.model_combo)
        model_select_layout.addStretch()
        layout.addLayout(model_select_layout)

        # Model description - shows supported cloning types
        self.model_description = BodyLabel(
            "Select a model to see voice cloning options"
        )
        self.model_description.setStyleSheet(
            "color: #888; font-size: 11px; margin-top: 5px;"
        )
        layout.addWidget(self.model_description)

    def _connect_signals(self):
        """Connect internal signals."""
        self.model_combo.currentIndexChanged.connect(self._on_combo_changed)

    def _on_combo_changed(self, index: int):
        """Handle combo box change."""
        model_id = self.model_combo.itemData(index)
        if model_id:
            self.model_changed.emit(model_id)

    def get_current_model(self) -> str:
        """Get currently selected model ID."""
        return self.model_combo.currentData()

    def set_current_model(self, model_id: str):
        """Set the current model by ID."""
        index = self.model_combo.findData(model_id)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)

    def update_description(self, model_id: str):
        """Update description based on selected model."""
        if model_id == "vibevoice":
            self.model_description.setText(
                "VibeVoice uses pre-generated .pt voice preset files for instant cloning"
            )
        else:
            self.model_description.setText(
                "Chatterbox uses reference audio to generate a cloned voice"
            )


class VibeVoiceSelectionCard(CardWidget):
    """Card widget for VibeVoice voice preset selection.

    Signals:
        voice_selected: Emitted when a voice is selected
        import_requested: Emitted when import button is clicked
        delete_requested: Emitted when delete button is clicked
        refresh_requested: Emitted when refresh button is clicked
    """

    voice_selected = Signal(str)  # voice_name
    import_requested = Signal()
    delete_requested = Signal()
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        vv_title = SubtitleLabel("VibeVoice Voice Presets")
        vv_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        layout.addWidget(vv_title)

        # Description
        vv_desc = BodyLabel(
            "Select from built-in voices or import custom .pt voice files"
        )
        vv_desc.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(vv_desc)

        # Voice list
        vv_list_layout = QHBoxLayout()
        self.voice_list = ListWidget()
        self.voice_list.setMaximumHeight(120)
        vv_list_layout.addWidget(self.voice_list)
        layout.addLayout(vv_list_layout)

        # Voice controls
        vv_controls_layout = QHBoxLayout()

        self.import_voice_btn = PushButton("Import .pt Voice")
        self.import_voice_btn.setToolTip("Import a custom .pt voice preset file")
        vv_controls_layout.addWidget(self.import_voice_btn)

        self.delete_voice_btn = PushButton("Delete Selected")
        self.delete_voice_btn.setToolTip("Delete the selected voice preset")
        vv_controls_layout.addWidget(self.delete_voice_btn)

        self.refresh_voices_btn = PushButton("Refresh")
        self.refresh_voices_btn.setToolTip("Refresh the voice list")
        vv_controls_layout.addWidget(self.refresh_voices_btn)

        vv_controls_layout.addStretch()
        layout.addLayout(vv_controls_layout)

        # Voice info
        self.voice_info = BodyLabel("Select a voice to use for cloning")
        self.voice_info.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.voice_info)

    def _connect_signals(self):
        """Connect internal signals."""
        self.voice_list.currentItemChanged.connect(self._on_voice_changed)
        self.import_voice_btn.clicked.connect(lambda: self.import_requested.emit())
        self.delete_voice_btn.clicked.connect(lambda: self.delete_requested.emit())
        self.refresh_voices_btn.clicked.connect(lambda: self.refresh_requested.emit())

    def _on_voice_changed(self, current, previous):
        """Handle voice selection change."""
        if current:
            self.voice_selected.emit(current.text())

    def get_selected_voice(self) -> str | None:
        """Get currently selected voice name."""
        current_item = self.voice_list.currentItem()
        return current_item.text() if current_item else None

    def set_voice_count(self, count: int):
        """Update voice count display."""
        self.voice_info.setText(f"Found {count} voice presets")

    def set_selected_voice_display(self, voice_name: str):
        """Update display to show selected voice."""
        self.voice_info.setText(f"Selected voice: {voice_name}")

    def clear_voices(self):
        """Clear the voice list."""
        self.voice_list.clear()

    def add_voice(self, voice_name: str):
        """Add a voice to the list."""
        self.voice_list.addItem(voice_name)

    def find_and_select_voice(self, voice_name: str) -> bool:
        """Find and select a voice by name. Returns True if found."""
        items = self.voice_list.findItems(voice_name, Qt.MatchFlag.MatchExactly)
        if items:
            self.voice_list.setCurrentItem(items[0])
            return True
        return False

    def select_first_voice(self):
        """Select the first voice in the list."""
        if self.voice_list.count() > 0:
            self.voice_list.setCurrentRow(0)

    def show_not_found_message(self, directory: Path):
        """Show directory not found message."""
        self.voice_info.setText(f"Voices directory not found: {directory}")


class ChatterboxReferenceCard(CardWidget):
    """Card widget for Chatterbox reference audio selection.

    Signals:
        browse_requested: Emitted when browse button is clicked
    """

    browse_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        cb_title = SubtitleLabel("Chatterbox Reference Audio")
        cb_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        layout.addWidget(cb_title)

        # Description
        cb_desc = BodyLabel(
            "Provide a reference audio file to clone your voice (WAV, MP3, FLAC)"
        )
        cb_desc.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(cb_desc)

        # Reference audio selection
        ref_audio_layout = QHBoxLayout()
        ref_audio_layout.addWidget(BodyLabel("Reference Audio:"))

        self.ref_audio_path_edit = LineEdit()
        self.ref_audio_path_edit.setPlaceholderText("Path to reference audio file...")
        ref_audio_layout.addWidget(self.ref_audio_path_edit)

        self.browse_ref_audio_btn = PushButton("Browse")
        self.browse_ref_audio_btn.setToolTip("Browse for reference audio file")
        ref_audio_layout.addWidget(self.browse_ref_audio_btn)
        ref_audio_layout.addStretch()
        layout.addLayout(ref_audio_layout)

        # Audio preview info
        self.ref_audio_info = BodyLabel("No reference audio selected")
        self.ref_audio_info.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.ref_audio_info)

        # Hidden by default - shown when Chatterbox model is selected
        self.setVisible(False)

    def _connect_signals(self):
        """Connect internal signals."""
        self.browse_ref_audio_btn.clicked.connect(lambda: self.browse_requested.emit())

    def get_reference_audio_path(self) -> str:
        """Get the current reference audio path."""
        return self.ref_audio_path_edit.text()

    def set_reference_audio_path(self, path: str):
        """Set the reference audio path."""
        self.ref_audio_path_edit.setText(path)
        if path:
            audio_name = Path(path).name
            self.ref_audio_info.setText(f"Selected: {audio_name}")
        else:
            self.ref_audio_info.setText("No reference audio selected")


class TextInputCard(CardWidget):
    """Card widget for text input and language selection.

    Signals:
        text_changed: Emitted when text content changes (optional)
        language_changed: Emitted when language selection changes
    """

    text_changed = Signal(str)
    language_changed = Signal(str)  # language_code

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        text_title = SubtitleLabel("Text to Synthesize")
        text_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        layout.addWidget(text_title)

        # Text input
        self.text_edit = TextEdit()
        self.text_edit.setPlaceholderText(
            "Enter text to synthesize with cloned voice..."
        )
        self.text_edit.setMaximumHeight(150)
        layout.addWidget(self.text_edit)

        # Language selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(BodyLabel("Language:"))

        self.language_combo = ComboBox()
        supported_langs = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
        }
        for lang_code, lang_name in supported_langs.items():
            self.language_combo.addItem(lang_name, userData=lang_code)

        lang_layout.addWidget(self.language_combo)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)

    def _connect_signals(self):
        """Connect internal signals."""
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)

    def _on_text_changed(self):
        """Handle text change."""
        self.text_changed.emit(self.get_text())

    def _on_language_changed(self, index: int):
        """Handle language change."""
        lang_code = self.language_combo.itemData(index)
        if lang_code:
            self.language_changed.emit(lang_code)

    def get_text(self) -> str:
        """Get the current text input."""
        return self.text_edit.toPlainText().strip()

    def set_text(self, text: str):
        """Set the text input."""
        self.text_edit.setPlainText(text)

    def get_language_code(self) -> str:
        """Get the selected language code."""
        return self.language_combo.currentData()

    def set_language_code(self, lang_code: str):
        """Set the language by code."""
        index = self.language_combo.findData(lang_code)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)


class GenerationControlsCard(CardWidget):
    """Card widget for generation controls and status display.

    Signals:
        generate_requested: Emitted when generate button is clicked
        play_requested: Emitted when play button is clicked
        save_requested: Emitted when save button is clicked
    """

    generate_requested = Signal()
    play_requested = Signal()
    save_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        gen_title = SubtitleLabel("Generate")
        gen_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        layout.addWidget(gen_title)

        # Generate controls
        gen_controls_layout = QHBoxLayout()

        self.generate_btn = PrimaryPushButton("Generate Cloned Voice")
        self.generate_btn.setToolTip("Generate speech with the cloned voice")
        gen_controls_layout.addWidget(self.generate_btn)

        self.play_btn = PushButton("Play")
        self.play_btn.setToolTip("Play the generated audio")
        self.play_btn.setEnabled(False)
        gen_controls_layout.addWidget(self.play_btn)

        self.save_btn = PushButton("Save Audio")
        self.save_btn.setToolTip("Save the generated audio to file")
        self.save_btn.setEnabled(False)
        gen_controls_layout.addWidget(self.save_btn)

        gen_controls_layout.addStretch()
        layout.addLayout(gen_controls_layout)

        # Progress indicator
        self.progress_ring = IndeterminateProgressRing()
        self.progress_ring.setVisible(False)
        layout.addWidget(self.progress_ring, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status label
        self.status_label = BodyLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.status_label)

    def _connect_signals(self):
        """Connect internal signals."""
        self.generate_btn.clicked.connect(lambda: self.generate_requested.emit())
        self.play_btn.clicked.connect(lambda: self.play_requested.emit())
        self.save_btn.clicked.connect(lambda: self.save_requested.emit())

    def set_generating_state(self, is_generating: bool):
        """Update UI for generating state."""
        self.generate_btn.setEnabled(not is_generating)
        self.play_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.progress_ring.setVisible(is_generating)

    def set_ready_state(self, has_audio: bool = False):
        """Update UI for ready state."""
        self.generate_btn.setEnabled(True)
        self.play_btn.setEnabled(has_audio)
        self.save_btn.setEnabled(has_audio)
        self.progress_ring.setVisible(False)

    def set_status(self, message: str):
        """Set the status message."""
        self.status_label.setText(message)

    def clear_status(self):
        """Clear the status message."""
        self.status_label.setText("")
