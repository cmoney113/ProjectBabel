"""
Model Selectors Widget
Contains: ASR model selector, TTS model selector, voice selection combos
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Signal
from qfluentwidgets import BodyLabel, ComboBox, InfoBar


class ModelSelectorsWidget(QWidget):
    """ASR and TTS model selection controls"""

    # Signals
    asr_model_changed = Signal(str)  # model_id
    tts_model_changed = Signal(str)  # model_id
    kittentts_voice_changed = Signal(str)
    vibevoice_voice_changed = Signal(str)

    def __init__(self, voice_processor, tts_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("ModelSelectorsWidget")
        self.voice_processor = voice_processor
        self.tts_manager = tts_manager
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

    def _create_asr_layout(self) -> QHBoxLayout:
        """Create ASR model selection layout"""
        layout = QHBoxLayout()

        asr_label = BodyLabel("🎯 ASR Model (Speech→Text):")
        asr_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #e6edf3;")
        layout.addWidget(asr_label)

        self.asr_model_combo = ComboBox()
        self.asr_model_combo.setToolTip(
            "Select speech recognition model. Models: (accuracy/speed | scale=1-10) Canary (10 acc-5 speed+multilingual-25 langs)), Parakeet (8/7=balanced+multilingual-25 langs), SenseVoice (10/8.5=speed-daemon+super-accurate+multilingual-5 Asian langs))"
        )

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

        tts_label = BodyLabel("🔊 TTS Model (Text→Speech):")
        tts_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #e6edf3;")
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
