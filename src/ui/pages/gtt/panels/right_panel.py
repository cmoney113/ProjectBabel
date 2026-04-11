"""
Right Panel Component for GTT Page.
Contains NLP bar, voice control, and command history.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget
from qfluentwidgets import (
    SubtitleLabel, CaptionLabel, BodyLabel,
    LineEdit, PrimaryPushButton, ComboBox,
    IndeterminateProgressRing, InfoBar
)
from ..components.nlp_bar import NLPBar


class RightPanel(QWidget):
    """Right sidebar panel with NLP and voice controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(320)
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize right panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 15, 15, 15)
        layout.setSpacing(12)

        self._create_nlp_section(layout)
        layout.addSpacing(10)
        self._create_voice_section(layout)
        layout.addSpacing(10)
        self._create_history_section(layout)
        layout.addStretch()

    def _create_nlp_section(self, layout: QVBoxLayout) -> None:
        """Create NLP command section."""
        layout.addWidget(SubtitleLabel("💡 NLP Command"))
        badge = CaptionLabel("Powered by OmniProxy • MiniMax-M2.1 / Qwen3-Coder")
        badge.setStyleSheet("color: #4A90E2; font-weight: bold;")
        layout.addWidget(badge)

        self.nlp_input = LineEdit()
        self.nlp_input.setPlaceholderText("e.g., 'focus firefox and open new tab'")
        self.nlp_input.setMinimumHeight(40)
        self.nlp_input.setStyleSheet(self._get_input_style())
        self.nlp_input.returnPressed.connect(self.send_nlp_command)
        layout.addWidget(self.nlp_input)

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

        self.send_nlp_btn = PrimaryPushButton("🚀 Send to GTT")
        self.send_nlp_btn.setMinimumHeight(40)
        self.send_nlp_btn.clicked.connect(self.send_nlp_command)
        layout.addWidget(self.send_nlp_btn)

        self.nlp_progress = IndeterminateProgressRing()
        self.nlp_progress.setFixedSize(24, 24)
        self.nlp_progress.setVisible(False)
        layout.addWidget(self.nlp_progress, alignment=Qt.AlignmentFlag.AlignCenter)

    def _get_input_style(self) -> str:
        """Return input field stylesheet."""
        return """
            LineEdit { padding: 10px; font-size: 14px;
                border: 2px solid #30363d; border-radius: 8px;
                background-color: #1a1f26; color: #e6edf3; }
            LineEdit:focus { border-color: #1f6feb; }
        """

    def _create_voice_section(self, layout: QVBoxLayout) -> None:
        """Create voice control section."""
        layout.addWidget(SubtitleLabel("🎤 Voice Control"))
        self.voice_input_btn = PrimaryPushButton("🎤 Start Voice Command")
        self.voice_input_btn.setMinimumHeight(45)
        self.voice_input_btn.clicked.connect(self.start_voice_command)
        layout.addWidget(self.voice_input_btn)

        self.voice_status_label = BodyLabel("Ready")
        self.voice_status_label.setStyleSheet("color: #8b949e;")
        layout.addWidget(self.voice_status_label)

    def _create_history_section(self, layout: QVBoxLayout) -> None:
        """Create command history section."""
        layout.addWidget(SubtitleLabel("📜 Command History"))
        self.history_list = QListWidget()
        self.history_list.setStyleSheet(
            "QListWidget { background-color: #1a1f26; border: 1px solid #30363d; "
            "border-radius: 8px; color: #8b949e; font-size: 12px; }"
        )
        self.history_list.setMaximumHeight(120)
        layout.addWidget(self.history_list)

    def send_nlp_command(self) -> None:
        """Handle NLP command send."""
        nlp_text = self.nlp_input.text().strip()
        if not nlp_text:
            InfoBar.warning("Empty Input", "Please enter a command", parent=self.parent(), duration=2000)
            return
        self.history_list.addItem(f"📝 {nlp_text}")
        self.nlp_progress.setVisible(True)
        if hasattr(self.parent(), 'send_nlp_command'):
            self.parent().send_nlp_command()

    def start_voice_command(self) -> None:
        """Handle voice command start."""
        if hasattr(self.parent(), 'start_voice_command'):
            self.parent().start_voice_command()

    def set_voice_status(self, status: str, color: str = "#8b949e") -> None:
        """Update voice status label."""
        self.voice_status_label.setText(status)
        self.voice_status_label.setStyleSheet(f"color: {color};")

    def set_nlp_progress(self, visible: bool) -> None:
        """Show/hide NLP progress indicator."""
        self.nlp_progress.setVisible(visible)

    def clear_nlp_input(self) -> None:
        """Clear NLP input field."""
        self.nlp_input.clear()

    def get_nlp_model(self) -> str:
        """Get selected NLP model."""
        return self.nlp_model_combo.currentText()
