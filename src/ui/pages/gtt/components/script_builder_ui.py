"""
Script Builder UI Components.
Provides UI creation methods for script builder panel.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QListWidget
)
from qfluentwidgets import (
    SubtitleLabel, BodyLabel, StrongBodyLabel,
    PrimaryPushButton, PushButton, ComboBox,
    TransparentToolButton, FluentIcon, SwitchButton,
    IndeterminateProgressRing
)


class ScriptBuilderUI:
    """UI component builder for ScriptBuilderPanel."""

    @staticmethod
    def create_title() -> SubtitleLabel:
        """Create section title."""
        title = SubtitleLabel("Script Builder")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        return title

    @staticmethod
    def create_command_combo(commands: list) -> ComboBox:
        """Create command type combo box."""
        combo = ComboBox()
        combo.setMinimumHeight(40)
        combo.addItems(commands)
        return combo

    @staticmethod
    def create_ai_button() -> TransparentToolButton:
        """Create AI generator button."""
        btn = TransparentToolButton(FluentIcon.ROBOT)
        btn.setToolTip("✨ AI Command Generator")
        btn.setMinimumHeight(40)
        return btn

    @staticmethod
    def create_params_scroll() -> tuple:
        """Create scrollable params area. Returns (scroll, layout)."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(200)
        scroll.setStyleSheet(
            "QScrollArea { background-color: #1a1f26; border: 1px solid #30363d; border-radius: 8px; }"
        )
        params_widget = QWidget()
        params_layout = QVBoxLayout(params_widget)
        params_layout.setContentsMargins(10, 10, 10, 10)
        params_layout.setSpacing(8)
        scroll.setWidget(params_widget)
        return scroll, params_layout

    @staticmethod
    def create_script_list() -> QListWidget:
        """Create script list widget."""
        list_widget = QListWidget()
        list_widget.setStyleSheet(ScriptBuilderUI._get_list_style())
        list_widget.setMinimumHeight(300)
        return list_widget

    @staticmethod
    def _get_list_style() -> str:
        """Return list stylesheet."""
        return """
            QListWidget { background-color: #1a1f26; border: 1px solid #30363d;
                border-radius: 8px; color: #e6edf3; font-size: 13px; }
            QListWidget::item { padding: 10px; border-radius: 4px; }
            QListWidget::item:selected { background-color: #1f6feb; }
        """

    @staticmethod
    def create_control_buttons() -> dict:
        """Create control buttons. Returns dict of buttons."""
        return {
            'remove': ScriptBuilderUI._create_btn("Remove Selected", 35),
            'clear': ScriptBuilderUI._create_btn("Clear All", 35),
            'export': ScriptBuilderUI._create_btn("📤 Export", 35),
            'import': ScriptBuilderUI._create_btn("📥 Import", 35),
        }

    @staticmethod
    def _create_btn(text: str, height: int) -> PushButton:
        """Create push button with min height."""
        btn = PushButton(text)
        btn.setMinimumHeight(height)
        return btn

    @staticmethod
    def create_dry_run_switch() -> SwitchButton:
        """Create dry-run toggle switch."""
        switch = SwitchButton()
        switch.setChecked(False)
        switch.setOnText("Preview only")
        switch.setOffText("Execute")
        return switch

    @staticmethod
    def create_execute_button() -> PrimaryPushButton:
        """Create execute script button."""
        btn = PrimaryPushButton("▶ Execute Script")
        btn.setMinimumHeight(45)
        btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        return btn

    @staticmethod
    def create_progress_indicator() -> tuple:
        """Create progress indicator. Returns (container, ring, label)."""
        container = QWidget()
        container.setStyleSheet("background-color: #1a1f26; border-radius: 8px; padding: 10px;")
        progress_layout = QVBoxLayout(container)
        ring = IndeterminateProgressRing()
        ring.setFixedSize(32, 32)
        ring.setVisible(False)
        progress_layout.addWidget(ring, alignment=Qt.AlignmentFlag.AlignCenter)
        label = BodyLabel("Executing...")
        label.setStyleSheet("color: #8b949e;")
        label.setVisible(False)
        progress_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
        container.setVisible(False)
        return container, ring, label

    @staticmethod
    def get_commands() -> list:
        """Get available GTT commands."""
        return [
            "Focus Window", "Close Window", "Maximize Window", "Minimize Window",
            "Unmaximize Window", "Unminimize Window", "Activate Window",
            "Move Window", "Resize Window", "Launch App", "Type Text", "Send Keys",
            "Screenshot", "OCR Active Window", "OCR File", "Save Layout", "Restore Layout",
            "Snap Window", "Register Hotkey Script", "Register Hotkey Input",
            "Add Macro", "Remove Macro", "GNOME Eval", "GNOME Notify", "Wait",
            "TermPipe Shell Command", "✨ Command (AI-Powered)",
        ]
