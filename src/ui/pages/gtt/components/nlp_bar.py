"""
NLP Bar Component for GTT.
Provides natural language command input with AI model selection.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    SubtitleLabel, CaptionLabel, BodyLabel,
    LineEdit, PrimaryPushButton, ComboBox,
    IndeterminateProgressRing, InfoBar
)


class NLPBar(QWidget):
    """NLP command input bar with model selection."""

    command_sent = Signal(str)  # Emits command text

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize NLP bar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Title and badge
        layout.addWidget(SubtitleLabel("💡 NLP Command"))
        badge = CaptionLabel("Powered by OmniProxy • MiniMax-M2.1 / Qwen3-Coder")
        badge.setStyleSheet("color: #4A90E2; font-weight: bold;")
        layout.addWidget(badge)

        # Input field
        self.nlp_input = LineEdit()
        self.nlp_input.setPlaceholderText("e.g., 'focus firefox and open new tab'")
        self.nlp_input.setMinimumHeight(40)
        self.nlp_input.setStyleSheet(self._get_input_style())
        self.nlp_input.returnPressed.connect(self.send_command)
        layout.addWidget(self.nlp_input)

        # Model selector
        model_layout = QHBoxLayout()
        model_layout.addWidget(BodyLabel("Model:"))
        self.nlp_model_combo = ComboBox()
        self.nlp_model_combo.setMinimumHeight(35)
        self.nlp_model_combo.addItems([
            "qwen3-coder-plus (Fastest)",
            "minimax-m2.1 (Best for code)",
            "kimi-k2 (Deep reasoning)",
            "deepseek-v3.2 (Balanced)",
        ])
        model_layout.addWidget(self.nlp_model_combo)
        layout.addLayout(model_layout)

        # Send button
        self.send_nlp_btn = PrimaryPushButton("🚀 Send to GTT")
        self.send_nlp_btn.setMinimumHeight(40)
        self.send_nlp_btn.clicked.connect(self.send_command)
        layout.addWidget(self.send_nlp_btn)

        # Progress indicator
        self.nlp_progress = IndeterminateProgressRing()
        self.nlp_progress.setFixedSize(24, 24)
        self.nlp_progress.setVisible(False)
        layout.addWidget(self.nlp_progress, alignment=Qt.AlignmentFlag.AlignCenter)

    def _get_input_style(self) -> str:
        """Return input field stylesheet."""
        return """
            LineEdit {
                padding: 10px; font-size: 14px;
                border: 2px solid #30363d; border-radius: 8px;
                background-color: #1a1f26; color: #e6edf3;
            }
            LineEdit:focus { border-color: #1f6feb; }
        """

    def send_command(self) -> None:
        """Send NLP command."""
        nlp_text = self.nlp_input.text().strip()
        if not nlp_text:
            InfoBar.warning("Empty Input", "Please enter a command", parent=self.parent(), duration=2000)
            return
        self.command_sent.emit(nlp_text)

    def set_progress(self, visible: bool) -> None:
        """Show/hide progress indicator."""
        self.nlp_progress.setVisible(visible)

    def clear_input(self) -> None:
        """Clear input field."""
        self.nlp_input.clear()

    def get_model(self) -> str:
        """Get selected model name."""
        return self.nlp_model_combo.currentText()
