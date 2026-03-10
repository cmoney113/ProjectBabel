"""
Transcription Panel Widget
Contains: Transcription display, custom text toggle, play button
"""

import re
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Signal
from qfluentwidgets import BodyLabel, SwitchButton, PushButton, TextEdit, CardWidget, InfoBar


class TranscriptionPanelWidget(QWidget):
    """Transcription display and custom text input"""

    # Signals
    custom_text_toggled = Signal(bool)
    play_text_requested = Signal(str)
    transcription_updated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TranscriptionPanelWidget")
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Card container
        self.card = CardWidget()
        card_layout = QVBoxLayout(self.card)

        # Title
        title = BodyLabel("Your Speech:")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #e6edf3;")
        card_layout.addWidget(title)

        # Transcription display
        self.transcription_display = TextEdit()
        self.transcription_display.setReadOnly(True)
        self.transcription_display.setMaximumHeight(150)
        self.transcription_display.setStyleSheet("""
            TextEdit {
                background-color: #1a1f26;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 14px;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
                font-size: 15px;
                line-height: 1.6;
                selection-background-color: #238636;
                selection-color: #ffffff;
            }
            TextEdit:hover {
                border-color: #484f58;
            }
            QTextEdit:disabled {
                background-color: #161b22;
                color: #8b949e;
            }
        """)
        card_layout.addWidget(self.transcription_display)

        # Custom text toggle + play button
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(BodyLabel("📝 Custom Text Mode:"))

        self.custom_text_toggle = SwitchButton()
        self.custom_text_toggle.setChecked(False)
        self.custom_text_toggle.checkedChanged.connect(self._on_custom_text_toggled)
        self.custom_text_toggle.setToolTip(
            "Enable to type/paste text, URLs, or search queries. URLs are fetched & read. Searches show results to select."
        )
        custom_layout.addWidget(self.custom_text_toggle)

        self.play_text_btn = PushButton("▶ Play")
        self.play_text_btn.setToolTip(
            "Play the entered text via TTS. Works with plain text, URLs (fetches article), or search queries."
        )
        self.play_text_btn.clicked.connect(self._on_play_text_clicked)
        self.play_text_btn.setEnabled(False)
        self.play_text_btn.setStyleSheet("""
            PushButton {
                background-color: #238636;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 6px;
            }
            PushButton:hover { background-color: #2ea043; }
            PushButton:disabled { background-color: #30363d; color: #8b949e; }
        """)
        custom_layout.addWidget(self.play_text_btn)
        custom_layout.addStretch()
        card_layout.addLayout(custom_layout)

        layout.addWidget(self.card)

    # Signal handlers
    def _on_custom_text_toggled(self, checked: bool):
        """Handle custom text mode toggle"""
        self.transcription_display.setReadOnly(not checked)
        if checked:
            self.transcription_display.setPlaceholderText(
                "Enter custom text here and click Play..."
            )
            self.play_text_btn.setVisible(True)
            self.play_text_btn.setEnabled(True)
            self.transcription_display.clear()
            self.transcription_display.setFocus()
        else:
            self.transcription_display.setPlaceholderText("")
            self.play_text_btn.setVisible(False)
            self.play_text_btn.setEnabled(False)

        self.custom_text_toggled.emit(checked)

    def _on_play_text_clicked(self):
        """Handle play button click"""
        text = self.transcription_display.toPlainText().strip()
        if not text:
            InfoBar.warning(
                "No Text",
                "Please enter text to play",
                parent=self,
                duration=2000,
            )
            return

        self.play_text_requested.emit(text)

    # Public API
    def append_transcription(self, text: str):
        """Append text to transcription display"""
        current_text = self.transcription_display.toPlainText()
        if current_text and not current_text.endswith("\n"):
            self.transcription_display.append("")
        self.transcription_display.append(text)

        # Auto-scroll to bottom
        self.transcription_display.verticalScrollBar().setValue(
            self.transcription_display.verticalScrollBar().maximum()
        )

        self.transcription_updated.emit(text)

    def get_transcription_text(self) -> str:
        """Get current transcription text"""
        return self.transcription_display.toPlainText()

    def clear_transcription(self):
        """Clear transcription display"""
        self.transcription_display.clear()

    def set_custom_text_mode(self, enabled: bool):
        """Set custom text mode enabled state"""
        self.custom_text_toggle.setChecked(enabled)

    def is_custom_text_enabled(self) -> bool:
        """Check if custom text mode is enabled"""
        return self.custom_text_toggle.isChecked()

    def _is_url(self, text: str) -> bool:
        """Check if text is a URL"""
        url_pattern = re.compile(
            r"^(https?://)?"
            r"(?:[-\w.]|(?:%[\da-fA-F]{2}))+"
            r"(?::\d+)?"
            r"(?:/|$|#|\?)",
            re.IGNORECASE,
        )
        return bool(url_pattern.match(text)) or text.startswith(
            ("http://", "https://")
        )

    def _is_search_query(self, text: str) -> bool:
        """Check if text looks like a search query"""
        search_keywords = [
            "what",
            "how",
            "why",
            "when",
            "where",
            "who",
            "explain",
            "search",
            "find",
            "latest",
            "news",
            "?",
            "tell me",
        ]
        return any(
            text.lower().startswith(kw) or f" {kw}" in text.lower()
            for kw in search_keywords
        )
