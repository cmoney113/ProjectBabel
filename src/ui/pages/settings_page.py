"""
Settings Page - Comprehensive settings management for ASR, TTS, VAD, and LLM
"""

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from qfluentwidgets import (
    SubtitleLabel,
    BodyLabel,
    PushButton,
    ComboBox,
    LineEdit,
    SpinBox,
    CardWidget,
    SmoothScrollArea,
    ToggleButton,
    InfoBar,
    SwitchButton,
)


class SettingsPage(QWidget):
    """Comprehensive settings page for all model configurations"""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.settings_manager = main_window.get_settings_manager()

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.setObjectName("settings_page")

        # Header
        header_layout = QHBoxLayout()
        title = SubtitleLabel("Settings")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Scroll area for settings
        scroll_area = SmoothScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # ASR Settings Section
        asr_settings_card = self._create_asr_settings_card()
        scroll_layout.addWidget(asr_settings_card)

        # TTS Settings Section
        tts_settings_card = self._create_tts_settings_card()
        scroll_layout.addWidget(tts_settings_card)

        # General Settings Section
        general_settings_card = self._create_general_settings_card()
        scroll_layout.addWidget(general_settings_card)

        # Save Settings Button
        save_layout = QHBoxLayout()
        self.save_settings_btn = PushButton("Save Settings")
        self.save_settings_btn.clicked.connect(self.save_all_settings)
        save_layout.addWidget(self.save_settings_btn)
        save_layout.addStretch()
        scroll_layout.addLayout(save_layout)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

    def _create_asr_settings_card(self):
        """Create ASR settings card"""
        card = CardWidget()
        layout = QVBoxLayout(card)

        title = SubtitleLabel("ASR Model Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title)

        # ASR Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(BodyLabel("ASR Model:"))
        self.asr_model_combo = ComboBox()
        from src.languages import CANARY_LANGUAGES

        for lang_code, lang_name in CANARY_LANGUAGES.items():
            self.asr_model_combo.addItem(lang_name, userData=lang_code)
        current_asr = self.settings_manager.get("asr_model", "en")
        index = self.asr_model_combo.findData(current_asr)
        if index >= 0:
            self.asr_model_combo.setCurrentIndex(index)
        model_layout.addWidget(self.asr_model_combo)
        model_layout.addStretch()
        layout.addLayout(model_layout)

        # Language for ASR
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(BodyLabel("Language:"))
        self.asr_language_combo = ComboBox()
        languages = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic",
            "hi": "Hindi",
        }
        for lang_code, lang_name in languages.items():
            self.asr_language_combo.addItem(lang_name, userData=lang_code)
        current_lang = self.settings_manager.get("target_language", "en")
        index = self.asr_language_combo.findData(current_lang)
        if index >= 0:
            self.asr_language_combo.setCurrentIndex(index)
        lang_layout.addWidget(self.asr_language_combo)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)

        return card

    def _create_tts_settings_card(self):
        """Create TTS settings card"""
        card = CardWidget()
        layout = QVBoxLayout(card)

        title = SubtitleLabel("TTS Model Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title)

        # TTS Model selection - use dynamic registry
        model_layout = QHBoxLayout()
        model_layout.addWidget(BodyLabel("TTS Model:"))
        self.tts_model_combo = ComboBox()
        # Use dynamic model registry
        from src.model_registry import ModelRegistry
        registry = ModelRegistry()
        for model in registry.get_tts_models():
            self.tts_model_combo.addItem(model.name, userData=model.id)
        current_tts = self.settings_manager.get("tts_model", "chatterbox-fp16")
        index = self.tts_model_combo.findData(current_tts)
        if index >= 0:
            self.tts_model_combo.setCurrentIndex(index)
        model_layout.addWidget(self.tts_model_combo)
        model_layout.addStretch()
        layout.addLayout(model_layout)

        # TTS Language
        tts_lang_layout = QHBoxLayout()
        tts_lang_layout.addWidget(BodyLabel("TTS Language:"))
        self.tts_language_combo = ComboBox()
        current_tts = self.settings_manager.get("tts_model", "chatterbox-fp16")
        # Use model registry for languages
        from src.model_registry import ModelRegistry
        registry = ModelRegistry()
        current_model = registry.get_model(current_tts)
        if current_model and current_model.language_options:
            for lang in current_model.language_options:
                lang_name = lang.upper()
                self.tts_language_combo.addItem(lang_name, userData=lang)
        else:
            self.tts_language_combo.addItem("English", userData="en")
        current_tts_lang = self.settings_manager.get("tts_language", "en")
        index = self.tts_language_combo.findData(current_tts_lang)
        if index >= 0:
            self.tts_language_combo.setCurrentIndex(index)
        tts_lang_layout.addWidget(self.tts_language_combo)
        tts_lang_layout.addStretch()
        layout.addLayout(tts_lang_layout)

        # Streaming Mode Toggle (for VibeVoice)
        streaming_layout = QHBoxLayout()
        streaming_layout.addWidget(BodyLabel("Streaming Mode (VibeVoice):"))
        self.streaming_toggle = SwitchButton()
        self.streaming_toggle.setChecked(
            self.settings_manager.get("tts_streaming", False)
        )
        self.streaming_toggle.setEnabled(current_tts == "vibevoice-realtime")
        streaming_layout.addWidget(self.streaming_toggle)
        streaming_layout.addStretch()
        layout.addLayout(streaming_layout)

        # Streaming info label
        streaming_info = BodyLabel(
            "Enable for ~300ms first audio latency (VibeVoice only)"
        )
        streaming_info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(streaming_info)

        # Voice Cloning Section (VibeVoice only)
        if current_tts == "vibevoice":
            voice_clone_header = BodyLabel("🎤 Voice Cloning (VibeVoice)")
            voice_clone_header.setStyleSheet("font-weight: bold; color: #e6edf3; margin-top: 10px;")
            layout.addWidget(voice_clone_header)
            
            clone_info = BodyLabel(
                "VibeVoice supports voice cloning. Place .pt voice files in:\n"
                "~/models/VibeVoiceRealtime05b/voices/"
            )
            clone_info.setStyleSheet("color: #8b949e; font-size: 11px;")
            layout.addWidget(clone_info)
            
            # Voice selection for cloned voices
            voice_layout = QHBoxLayout()
            voice_layout.addWidget(BodyLabel("Voice:"))
            self.clone_voice_combo = ComboBox()
            # Populate with available voices
            import os
            voice_dir = os.path.expanduser("~/new-projects/voice_ai/models/VibeVoiceRealtime05b/voices")
            if os.path.exists(voice_dir):
                for f in os.listdir(voice_dir):
                    if f.endswith(".pt"):
                        voice_name = f.replace(".pt", "")
                        self.clone_voice_combo.addItem(voice_name, userData=voice_name)
            current_voice = self.settings_manager.get("vibevoice_voice", "Carter")
            idx = self.clone_voice_combo.findData(current_voice)
            if idx >= 0:
                self.clone_voice_combo.setCurrentIndex(idx)
            voice_layout.addWidget(self.clone_voice_combo)
            voice_layout.addStretch()
            layout.addLayout(voice_layout)

        # Auto-save Toggle
        auto_save_layout = QHBoxLayout()
        auto_save_layout.addWidget(BodyLabel("Auto-save TTS Output:"))
        self.auto_save_toggle = SwitchButton()
        self.auto_save_toggle.setChecked(
            self.settings_manager.get("tts_auto_save", True)
        )
        auto_save_layout.addWidget(self.auto_save_toggle)
        auto_save_layout.addStretch()
        layout.addLayout(auto_save_layout)

        # Output Directory
        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(BodyLabel("Output Directory:"))
        self.output_dir_edit = LineEdit()
        self.output_dir_edit.setText(
            self.settings_manager.get(
                "tts_output_dir", str(Path.home() / "Documents" / "babel" / "outputs")
            )
        )
        output_dir_layout.addWidget(self.output_dir_edit)

        self.browse_btn = PushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_output_dir)
        output_dir_layout.addWidget(self.browse_btn)
        layout.addLayout(output_dir_layout)

        return card

    def _create_general_settings_card(self):
        """Create general settings card"""
        card = CardWidget()
        layout = QVBoxLayout(card)

        title = SubtitleLabel("General Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title)

        # VAD Settings
        vad_layout = QHBoxLayout()
        vad_layout.addWidget(BodyLabel("VAD Energy Threshold:"))
        self.vad_energy_spin = SpinBox()
        self.vad_energy_spin.setRange(1, 100)
        self.vad_energy_spin.setValue(
            int(self.settings_manager.get("energy_threshold", 0.02) * 1000)
        )
        self.vad_energy_spin.setSuffix(" (x0.001)")
        vad_layout.addWidget(self.vad_energy_spin)
        vad_layout.addStretch()
        layout.addLayout(vad_layout)

        # Silence Timeout
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(BodyLabel("Silence Timeout:"))
        self.vad_timeout_spin = SpinBox()
        self.vad_timeout_spin.setRange(100, 5000)
        self.vad_timeout_spin.setValue(
            self.settings_manager.get("silence_timeout_ms", 1000)
        )
        self.vad_timeout_spin.setSuffix("ms")
        timeout_layout.addWidget(self.vad_timeout_spin)
        timeout_layout.addStretch()
        layout.addLayout(timeout_layout)

        # Groq API Key
        api_layout = QHBoxLayout()
        api_layout.addWidget(BodyLabel("Groq API Key:"))
        self.groq_api_edit = LineEdit()
        self.groq_api_edit.setText(self.settings_manager.get("groq_api_key", ""))
        self.groq_api_edit.setEchoMode(LineEdit.EchoMode.Password)
        api_layout.addWidget(self.groq_api_edit)
        api_layout.addStretch()
        layout.addLayout(api_layout)

        # Tavily API Key
        tavily_layout = QHBoxLayout()
        tavily_layout.addWidget(BodyLabel("Tavily API Key:"))
        self.tavily_api_edit = LineEdit()
        self.tavily_api_edit.setText(self.settings_manager.get("tavily_api_key", ""))
        self.tavily_api_edit.setEchoMode(LineEdit.EchoMode.Password)
        tavily_layout.addWidget(self.tavily_api_edit)
        tavily_layout.addStretch()
        layout.addLayout(tavily_layout)

        return card

    def browse_output_dir(self):
        """Browse for output directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.output_dir_edit.text()
        )
        if dir_path:
            self.output_dir_edit.setText(dir_path)

    def connect_signals(self):
        """Connect UI signals to handlers"""
        self.asr_model_combo.currentIndexChanged.connect(self.on_asr_model_changed)
        self.asr_language_combo.currentIndexChanged.connect(
            self.on_asr_language_changed
        )
        self.tts_model_combo.currentIndexChanged.connect(self.on_tts_model_changed)
        self.tts_language_combo.currentIndexChanged.connect(
            self.on_tts_language_changed
        )
        self.streaming_toggle.checkedChanged.connect(self.on_streaming_toggled)

    # === Event Handlers ===

    def on_asr_model_changed(self, index):
        """Handle ASR model selection change"""
        model_id = self.asr_model_combo.itemData(index)
        if model_id:
            self.settings_manager.set("asr_model", model_id)
            self.settings_manager.save_settings()

    def on_asr_language_changed(self, index):
        """Handle ASR language selection change"""
        lang_code = self.asr_language_combo.itemData(index)
        if lang_code:
            self.settings_manager.set("target_language", lang_code)
            self.settings_manager.save_settings()

    def on_tts_model_changed(self, index):
        """Handle TTS model selection change"""
        model_id = self.tts_model_combo.itemData(index)
        if model_id:
            self.settings_manager.set("tts_model", model_id)
            self._update_tts_language_combo(model_id)
            self.streaming_toggle.setEnabled(model_id == "vibevoice-realtime")
            self.settings_manager.save_settings()

    def on_tts_language_changed(self, index):
        """Handle TTS language selection change"""
        lang_code = self.tts_language_combo.itemData(index)
        if lang_code:
            self.settings_manager.set("tts_language", lang_code)
            self.settings_manager.save_settings()

    def on_streaming_toggled(self, checked):
        """Handle streaming mode toggle"""
        self.settings_manager.set("tts_streaming", checked)
        self.settings_manager.save_settings()

    def set_streaming_enabled(self, enabled):
        """Enable/disable streaming toggle based on TTS model"""
        self.streaming_toggle.setEnabled(enabled)

    def _update_tts_language_combo(self, model_id):
        """Update TTS language combo based on selected model"""
        from src.languages import TTS_MODELS

        self.tts_language_combo.blockSignals(True)
        self.tts_language_combo.clear()

        tts_langs = TTS_MODELS.get(model_id, {}).get("languages", {"en": "English"})
        for lang_code, lang_name in tts_langs.items():
            self.tts_language_combo.addItem(lang_name, userData=lang_code)

        # Set to current or default
        current_lang = self.settings_manager.get("tts_language", "en")
        index = self.tts_language_combo.findData(current_lang)
        if index >= 0:
            self.tts_language_combo.setCurrentIndex(index)
        else:
            self.tts_language_combo.setCurrentIndex(0)

        self.tts_language_combo.blockSignals(False)

    def save_all_settings(self):
        """Save all settings"""
        try:
            # ASR Settings
            self.settings_manager.set("asr_model", self.asr_model_combo.currentData())
            self.settings_manager.set(
                "target_language", self.asr_language_combo.currentData()
            )

            # TTS Settings
            self.settings_manager.set("tts_model", self.tts_model_combo.currentData())
            self.settings_manager.set(
                "tts_language", self.tts_language_combo.currentData()
            )
            self.settings_manager.set(
                "tts_streaming", self.streaming_toggle.isChecked()
            )
            self.settings_manager.set(
                "tts_auto_save", self.auto_save_toggle.isChecked()
            )
            self.settings_manager.set("tts_output_dir", self.output_dir_edit.text())

            # General Settings
            self.settings_manager.set(
                "energy_threshold", self.vad_energy_spin.value() / 1000.0
            )
            self.settings_manager.set(
                "silence_timeout_ms", self.vad_timeout_spin.value()
            )
            self.settings_manager.set("groq_api_key", self.groq_api_edit.text())
            self.settings_manager.set("tavily_api_key", self.tavily_api_edit.text())

            # Save to file
            self.settings_manager.save_settings()

            InfoBar.success(
                "Settings Saved",
                "All settings have been saved successfully",
                parent=self,
                duration=2000,
            )

        except Exception as e:
            InfoBar.error(
                "Save Error",
                f"Failed to save settings: {str(e)}",
                parent=self,
                duration=3000,
            )

    # === Public Methods for MainWindow ===

    def get_save_button(self):
        """Get save button for styling"""
        return self.save_settings_btn
