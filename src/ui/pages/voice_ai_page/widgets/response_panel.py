"""
Response Panel Widget
Contains: AI response display, verbosity selector, translation controls
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Signal
from qfluentwidgets import (
    BodyLabel,
    ComboBox,
    ToggleButton,
    CardWidget,
    InfoBar,
)
from src.markdown_display import ScrollableMarkdownDisplay


class ResponsePanelWidget(QWidget):
    """AI response display with verbosity and translation controls"""

    # Signals
    verbosity_changed = Signal(str)  # verbosity level
    translation_toggled = Signal(bool)
    target_language_changed = Signal(str)  # lang_code

    def __init__(self, tts_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("ResponsePanelWidget")
        self.tts_manager = tts_manager
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Card container
        self.card = CardWidget()
        card_layout = QVBoxLayout(self.card)

        # Response header
        header_layout = self._create_header_layout()
        card_layout.addLayout(header_layout)

        # Markdown display for response
        self.response_display = ScrollableMarkdownDisplay()
        self.response_display.setMaximumHeight(250)
        card_layout.addWidget(self.response_display)

        layout.addWidget(self.card)

    def _create_header_layout(self) -> QHBoxLayout:
        """Create response header with controls"""
        layout = QHBoxLayout()

        # Title
        response_title = BodyLabel("AI Response:")
        response_title.setStyleSheet("font-weight: bold;")
        layout.addWidget(response_title)
        layout.addStretch()

        # Verbosity selector
        verbosity_label = BodyLabel("Response:")
        verbosity_label.setStyleSheet("font-size: 12px; color: #888888;")
        layout.addWidget(verbosity_label)

        self.verbosity_combo = ComboBox()
        self.verbosity_combo.addItems(["Concise", "Balanced", "Detailed"])
        self.verbosity_combo.setCurrentIndex(1)  # Default to Balanced
        self.verbosity_combo.setFixedWidth(100)
        self.verbosity_combo.currentTextChanged.connect(self._on_verbosity_changed)
        layout.addWidget(self.verbosity_combo)

        # Translation toggle
        translate_label = BodyLabel("Translate:")
        translate_label.setStyleSheet(
            "font-size: 12px; color: #888888; margin-left: 15px;"
        )
        layout.addWidget(translate_label)

        self.translation_toggle = ToggleButton("", self)
        self.translation_toggle.setFixedWidth(50)
        self.translation_toggle.setChecked(False)
        self.translation_toggle.setToolTip("Enable translation service")
        self.translation_toggle.toggled.connect(self._on_translation_toggled)
        layout.addWidget(self.translation_toggle)

        # Target language selector
        target_lang_label = BodyLabel("Output:")
        target_lang_label.setStyleSheet(
            "font-size: 12px; color: #888888; margin-left: 15px;"
        )
        layout.addWidget(target_lang_label)

        self.target_language_combo = ComboBox()
        self.target_language_combo.setFixedWidth(120)
        self.target_language_combo.currentIndexChanged.connect(
            self._on_target_language_changed
        )
        self.target_language_combo.setEnabled(False)
        layout.addWidget(self.target_language_combo)

        return layout

    # Signal handlers
    def _on_verbosity_changed(self, text: str):
        """Handle verbosity change"""
        verbosity_map = {
            "Concise": "concise",
            "Balanced": "balanced",
            "Detailed": "detailed",
        }
        verbosity = verbosity_map.get(text, "balanced")
        InfoBar.info(
            "Response Style",
            f"Set to {text}",
            parent=self,
            duration=1500,
        )
        self.verbosity_changed.emit(verbosity)

    def _on_translation_toggled(self, checked: bool):
        """Handle translation toggle"""
        self.target_language_combo.setEnabled(checked)

        if checked:
            InfoBar.info(
                "Translation",
                "Translation enabled",
                parent=self,
                duration=1500,
            )
        else:
            InfoBar.info(
                "Translation",
                "Translation disabled - direct passthrough",
                parent=self,
                duration=1500,
            )

        self.translation_toggled.emit(checked)

    def _on_target_language_changed(self, index: int):
        """Handle target language change"""
        lang_code = self.target_language_combo.currentData()
        lang_name = self.target_language_combo.currentText()

        if lang_code == "" or lang_code is None:
            InfoBar.info(
                "Output Language",
                "Will use same as input (no translation)",
                parent=self,
                duration=1500,
            )
        else:
            InfoBar.info(
                "Output Language",
                f"Set to {lang_name}",
                parent=self,
                duration=1500,
            )

        self.target_language_changed.emit(lang_code or "en")

    # Public API
    def append_response(self, text: str):
        """Append text to response display"""
        current_text = self.response_display.toPlainText()
        if current_text and not current_text.endswith("\n"):
            self.response_display.append("")
        self.response_display.append(text)

        # Auto-scroll to bottom
        self.response_display.verticalScrollBar().setValue(
            self.response_display.verticalScrollBar().maximum()
        )

    def set_response(self, text: str):
        """Set response text (replace all)"""
        self.response_display.setMarkdown(text)

    def get_response_text(self) -> str:
        """Get current response text"""
        return self.response_display.toPlainText()

    def clear_response(self):
        """Clear response display"""
        self.response_display.clear()

    def get_verbosity(self) -> str:
        """Get current verbosity level"""
        verbosity_map = {
            "Concise": "concise",
            "Balanced": "balanced",
            "Detailed": "detailed",
        }
        return verbosity_map.get(self.verbosity_combo.currentText(), "balanced")

    def set_verbosity(self, verbosity: str):
        """Set verbosity level"""
        reverse_map = {
            "concise": "Concise",
            "balanced": "Balanced",
            "detailed": "Detailed",
        }
        text = reverse_map.get(verbosity, "Balanced")
        index = self.verbosity_combo.findText(text)
        if index >= 0:
            self.verbosity_combo.setCurrentIndex(index)

    def is_translation_enabled(self) -> bool:
        """Check if translation is enabled"""
        return self.translation_toggle.isChecked()

    def set_translation_enabled(self, enabled: bool):
        """Set translation enabled state"""
        self.translation_toggle.setChecked(enabled)

    def get_target_language(self) -> str:
        """Get target language code"""
        return self.target_language_combo.currentData() or "en"

    def set_target_language(self, lang_code: str):
        """Set target language"""
        index = self.target_language_combo.findData(lang_code)
        if index >= 0:
            self.target_language_combo.setCurrentIndex(index)

    def populate_target_languages(self, languages: dict):
        """Populate target language combo with supported languages"""
        self.target_language_combo.blockSignals(True)
        self.target_language_combo.clear()

        # Add "Same as input" option first
        self.target_language_combo.addItem("Same as input", userData="")

        # Add languages
        for lang_code, lang_name in sorted(languages.items(), key=lambda x: x[1]):
            self.target_language_combo.addItem(lang_name, userData=lang_code)

        # Default to English or first supported language
        default_lang = "en" if "en" in languages else list(languages.keys())[0]
        index = self.target_language_combo.findData(default_lang)
        if index >= 0:
            self.target_language_combo.setCurrentIndex(index)

        self.target_language_combo.blockSignals(False)
