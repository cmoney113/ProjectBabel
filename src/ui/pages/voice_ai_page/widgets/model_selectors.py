"""
Model Selectors Widget
Contains: ASR model selector, TTS model selector, voice selection combos
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Signal
from qfluentwidgets import BodyLabel, ComboBox, InfoBar, ToggleButton, PushButton

from src.settings_manager import SettingsManager
from .prompt_manager import PromptManagerDialog


class ModelSelectorsWidget(QWidget):
    """ASR and TTS model selection controls"""

    # Signals
    asr_model_changed = Signal(str)  # model_id
    tts_model_changed = Signal(str)  # model_id
    kittentts_voice_changed = Signal(str)
    vibevoice_voice_changed = Signal(str)
    dictation_mode_changed = Signal(bool)  # is_dictation_mode
    window_selected = Signal(str)  # window_id

    def __init__(
        self, voice_processor, tts_manager, recording_controls=None, parent=None
    ):
        super().__init__(parent)
        self.setObjectName("ModelSelectorsWidget")
        self.voice_processor = voice_processor
        self.tts_manager = tts_manager
        self.recording_controls = recording_controls
        self.settings_manager = SettingsManager()
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ASR Model selection
        self.asr_layout = self._create_asr_layout()
        layout.addLayout(self.asr_layout)

        # TTS Model selection
        self.tts_layout = self._create_tts_layout()
        layout.addLayout(self.tts_layout)

        # Prompt selection
        self.prompt_layout = self._create_prompt_layout()
        layout.addLayout(self.prompt_layout)

    def _create_asr_layout(self) -> QHBoxLayout:
        """Create ASR model selection layout with Dictation toggle"""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        # ASR Model icon
        asr_icon = BodyLabel("🎤")
        asr_icon.setStyleSheet("font-size: 14px;")
        layout.addWidget(asr_icon)

        self.asr_model_combo = ComboBox()
        self.asr_model_combo.setFixedWidth(200)
        self.asr_model_combo.setToolTip("Select speech recognition model")

        # Populate models
        asr_models = self.voice_processor.get_available_asr_models()
        for model_id, model_name in asr_models.items():
            self.asr_model_combo.addItem(model_name, userData=model_id)

        # Set current model
        current_asr = self.voice_processor.get_current_asr_model()
        index = self.asr_model_combo.findData(current_asr)
        if index >= 0:
            self.asr_model_combo.setCurrentIndex(index)

        self.asr_model_combo.currentIndexChanged.connect(self._on_asr_model_changed)
        layout.addWidget(self.asr_model_combo)

        layout.addStretch()

        return layout

    def _create_tts_layout(self) -> QHBoxLayout:
        """Create TTS model selection layout"""
        layout = QHBoxLayout()

        tts_label = BodyLabel("🔊")
        tts_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(tts_label)

        self.tts_model_combo = ComboBox()
        self.tts_model_combo.setToolTip(
            "Select text-to-speech model. VibeVoice supports streaming (~300ms latency) and voice cloning"
        )

        # Populate models
        tts_models = self.tts_manager.get_available_tts_models()
        for model_id, model_name in tts_models.items():
            self.tts_model_combo.addItem(model_name, userData=model_id)

        # Set current model
        current_tts = self.tts_manager.get_current_tts_model()
        index = self.tts_model_combo.findData(current_tts)
        if index >= 0:
            self.tts_model_combo.setCurrentIndex(index)

        self.tts_model_combo.currentIndexChanged.connect(self._on_tts_model_changed)
        layout.addWidget(self.tts_model_combo)

        # KittenTTS voice selection (initially hidden)
        self.kittentts_voice_combo = ComboBox()
        self.kittentts_voice_combo.addItems(
            ["Bella", "Jasper", "Luna", "Bruno", "Rosie", "Hugo", "Kiki", "Leo"]
        )
        self.kittentts_voice_combo.setCurrentIndex(1)  # Default to Jasper
        self.kittentts_voice_combo.setVisible(False)
        self.kittentts_voice_combo.currentTextChanged.connect(
            self._on_kittentts_voice_changed
        )
        layout.addWidget(self.kittentts_voice_combo)

        # VibeVoice voice selection (initially hidden)
        self.vibevoice_voice_combo = ComboBox()
        self.vibevoice_voice_combo.addItems(
            ["Carter", "Emma", "Fable", "Onyx", "Nova", "Shimmer"]
        )
        self.vibevoice_voice_combo.setCurrentIndex(0)  # Default to Carter
        self.vibevoice_voice_combo.setVisible(False)
        self.vibevoice_voice_combo.currentTextChanged.connect(
            self._on_vibevoice_voice_changed
        )
        layout.addWidget(self.vibevoice_voice_combo)

        layout.addStretch()
        return layout

    def _create_prompt_layout(self) -> QHBoxLayout:
        """Create prompt selection layout"""
        from .prompt_manager import PromptManagerDialog

        layout = QHBoxLayout()
        layout.setSpacing(10)

        # Prompt dropdown
        self.prompt_combo = ComboBox()
        self.prompt_combo.setFixedWidth(150)
        self.prompt_combo.setToolTip("Select LLM prompt style")

        # Load prompts from settings
        prompts = self.settings_manager.get("prompts", {})
        if not prompts:
            # Default prompts
            prompts = {
                "casual": "Casual - Friendly and conversational",
                "professional": "Professional - Formal and business-like",
                "coding": "Coding - Technical and precise",
                "sarcastic": "Sarcastic - Witty and ironic",
                "pirate": "Pirate - Arrr!",
            }

        for prompt_id, prompt_desc in prompts.items():
            self.prompt_combo.addItem(prompt_desc.split(" - ")[0], userData=prompt_id)

        # Load saved prompt or default to first
        saved_prompt = self.settings_manager.get("current_prompt", "casual")
        index = self.prompt_combo.findData(saved_prompt)
        if index >= 0:
            self.prompt_combo.setCurrentIndex(index)

        self.prompt_combo.currentIndexChanged.connect(self._on_prompt_changed)
        layout.addWidget(self.prompt_combo)

        # Edit prompts button
        self.edit_prompts_btn = PushButton("✏️")
        self.edit_prompts_btn.setToolTip("Manage prompts")
        self.edit_prompts_btn.clicked.connect(self._show_prompt_manager)
        layout.addWidget(self.edit_prompts_btn)

        layout.addStretch()
        return layout

    def _show_prompt_manager(self):
        """Show prompt management dialog"""
        from .prompt_manager import PromptManagerDialog

        dialog = PromptManagerDialog(self.settings_manager, self)
        dialog.prompts_changed.connect(self._populate_prompts)
        dialog.exec()

    # Signal handlers
    def _on_asr_model_changed(self, index: int):
        """Handle ASR model selection change"""
        model_id = self.asr_model_combo.itemData(index)
        if model_id:
            try:
                self.voice_processor.switch_asr_model(model_id)
                InfoBar.success(
                    "ASR Model Changed",
                    f"Switched to {self.asr_model_combo.currentText()}",
                    parent=self,
                    duration=2000,
                )
                self.asr_model_changed.emit(model_id)
            except Exception as e:
                InfoBar.error(
                    "ASR Model Error",
                    f"Failed to switch ASR model: {str(e)}",
                    parent=self,
                    duration=3000,
                )

    def _on_tts_model_changed(self, index: int):
        """Handle TTS model selection change"""
        model_id = self.tts_model_combo.itemData(index)
        if model_id:
            try:
                self.tts_manager.switch_tts_model(model_id)
                self.tts_model_changed.emit(model_id)
            except Exception as e:
                InfoBar.error(
                    "TTS Model Error",
                    f"Failed to switch TTS model: {str(e)}",
                    parent=self,
                    duration=3000,
                )

            # Update voice combo visibility
            is_kittentts = model_id == "kittentts"
            is_vibevoice = model_id == "vibevoice"
            self.kittentts_voice_combo.setVisible(is_kittentts)
            self.vibevoice_voice_combo.setVisible(is_vibevoice)

            # Show voice info
            if is_kittentts:
                InfoBar.info(
                    "KittenTTS Voice",
                    f"Voice: {self.kittentts_voice_combo.currentText()}",
                    parent=self,
                    duration=1500,
                )
            elif is_vibevoice:
                InfoBar.info(
                    "VibeVoice Voice",
                    f"Voice: {self.vibevoice_voice_combo.currentText()}",
                    parent=self,
                    duration=1500,
                )
            else:
                InfoBar.success(
                    "TTS Model Changed",
                    f"Switched to {self.tts_model_combo.currentText()}",
                    parent=self,
                    duration=2000,
                )

            self.tts_manager.set_current_tts_model(model_id)

    def _on_kittentts_voice_changed(self, voice: str):
        """Handle KittenTTS voice change"""
        self.kittentts_voice_changed.emit(voice)

    def _on_vibevoice_voice_changed(self, voice: str):
        """Handle VibeVoice voice change"""
        self.vibevoice_voice_changed.emit(voice)

    # Public API
    def get_current_asr_model(self) -> str:
        """Get current ASR model ID"""
        return self.asr_model_combo.currentData() or ""

    def get_current_tts_model(self) -> str:
        """Get current TTS model ID"""
        return self.tts_model_combo.currentData() or ""

    def get_kittentts_voice(self) -> str:
        """Get selected KittenTTS voice"""
        return self.kittentts_voice_combo.currentText()

    def get_vibevoice_voice(self) -> str:
        """Get selected VibeVoice voice"""
        return self.vibevoice_voice_combo.currentText()

    def set_kittentts_voice(self, voice: str):
        """Set KittenTTS voice"""
        index = self.kittentts_voice_combo.findText(voice)
        if index >= 0:
            self.kittentts_voice_combo.setCurrentIndex(index)

    def set_vibevoice_voice(self, voice: str):
        """Set VibeVoice voice"""
        index = self.vibevoice_voice_combo.findText(voice)
        if index >= 0:
            self.vibevoice_voice_combo.setCurrentIndex(index)

    # Dictation mode handlers
    def _on_dictation_toggled(self, checked: bool):
        """Handle dictation mode toggle"""
        if checked:
            self._populate_window_list()
            self.recording_controls.inject_window_combo.setEnabled(True)
        else:
            self.recording_controls.inject_window_combo.setEnabled(False)
        self.dictation_mode_changed.emit(checked)

    def _on_window_changed(self, index: int):
        """Handle window selection change"""
        window_id = self.recording_controls.inject_window_combo.currentData()
        if window_id:
            self.window_selected.emit(window_id)

    def _populate_prompts(self):
        """Populate prompt combo with saved prompts"""
        prompts = self.settings_manager.get_prompts()
        current_prompt = self.settings_manager.get_current_prompt()

        self.prompt_combo.blockSignals(True)
        self.prompt_combo.clear()

        for name in prompts.keys():
            self.prompt_combo.addItem(name, userData=name)

        index = self.prompt_combo.findData(current_prompt)
        if index >= 0:
            self.prompt_combo.setCurrentIndex(index)

        self.prompt_combo.blockSignals(False)

    def _on_prompt_changed(self, index: int):
        """Handle prompt selection change"""
        prompt_name = self.prompt_combo.currentData()
        if prompt_name:
            self.settings_manager.set_current_prompt(prompt_name)

    def _on_manage_prompts(self):
        """Open prompt management dialog"""
        from .prompt_manager import PromptManagerDialog

        dialog = PromptManagerDialog(self.settings_manager, self)
        dialog.prompts_changed.connect(self._populate_prompts)
        dialog.exec()

    def _populate_window_list(self):
        """Populate window combo with open windows from gtt --list"""
        windows = self.tts_manager.get_window_list()

        self.recording_controls.inject_window_combo.blockSignals(True)
        self.recording_controls.inject_window_combo.clear()

        if not windows:
            self.recording_controls.inject_window_combo.addItem(
                "No windows found", userData=None
            )
            InfoBar.warning(
                "No Windows",
                "No open windows found via gtt",
                parent=self,
                duration=2000,
            )
        else:
            self.recording_controls.inject_window_combo.addItem(
                "Inject Text...", userData=None
            )
            for w in windows:
                title = w.get("title", "Unknown")[:50]
                wm_class = w.get("wm_class", "")
                display_text = f"{title} ({wm_class})" if wm_class else title
                self.recording_controls.inject_window_combo.addItem(
                    display_text, userData=w.get("id")
                )

        self.recording_controls.inject_window_combo.blockSignals(False)

    def is_dictation_mode(self) -> bool:
        """Check if dictation mode is enabled"""
        return self.recording_controls.dictation_toggle.isChecked()

    def set_dictation_mode(self, enabled: bool):
        """Set dictation mode enabled state"""
        self.recording_controls.dictation_toggle.setChecked(enabled)
        if enabled:
            self._populate_window_list()
            self.recording_controls.inject_window_combo.setEnabled(True)
        else:
            self.recording_controls.inject_window_combo.setEnabled(False)

    def get_selected_window_id(self) -> str | None:
        """Get selected window ID for dictation"""
        if self.is_dictation_mode():
            return self.recording_controls.inject_window_combo.currentData()
        return None
