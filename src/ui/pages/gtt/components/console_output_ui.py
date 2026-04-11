"""
Console Output UI Helper.
Provides UI creation methods for ConsoleOutputPanel.
"""

from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QFileDialog, QApplication
from qfluentwidgets import (
    ToggleButton, SearchLineEdit, SwitchButton, TransparentToolButton,
    FluentIcon, TextEdit, CaptionLabel, InfoBar
)


class ConsoleOutputUI:
    """UI component builder for ConsoleOutputPanel."""

    @staticmethod
    def create_filter_buttons(toolbar: QHBoxLayout) -> dict:
        """Create filter toggle buttons."""
        buttons = {}
        for name in ["info", "error", "success", "command"]:
            btn = ToggleButton(name.upper())
            btn.setChecked(True)
            btn.setMinimumHeight(32)
            toolbar.addWidget(btn)
            buttons[f"filter_{name}"] = btn
        return buttons

    @staticmethod
    def create_search_box(toolbar: QHBoxLayout, on_change_callback) -> SearchLineEdit:
        """Create search input box."""
        search_box = SearchLineEdit()
        search_box.setPlaceholderText("Search console...")
        search_box.setMaximumWidth(200)
        search_box.setMinimumHeight(32)
        search_box.textChanged.connect(on_change_callback)
        toolbar.addWidget(search_box)
        return search_box

    @staticmethod
    def create_auto_scroll_toggle(toolbar: QHBoxLayout) -> SwitchButton:
        """Create auto-scroll toggle switch."""
        switch = SwitchButton()
        switch.setChecked(True)
        switch.setOnText("Auto-scroll")
        switch.setOffText("Auto-scroll")
        switch.setMinimumWidth(100)
        toolbar.addWidget(switch)
        return switch

    @staticmethod
    def create_action_buttons(toolbar: QHBoxLayout, callbacks: dict) -> dict:
        """Create clear, copy, save action buttons."""
        buttons = {
            "clear_btn": ConsoleOutputUI._create_tool_btn(
                FluentIcon.DELETE, "Clear console (Ctrl+L)", callbacks.get("clear")
            ),
            "copy_btn": ConsoleOutputUI._create_tool_btn(
                FluentIcon.COPY, "Copy all", callbacks.get("copy")
            ),
            "save_btn": ConsoleOutputUI._create_tool_btn(
                FluentIcon.SAVE, "Save to file", callbacks.get("save")
            ),
        }
        for btn in buttons.values():
            toolbar.addWidget(btn)
        return buttons

    @staticmethod
    def _create_tool_btn(icon, tooltip, callback) -> TransparentToolButton:
        """Create tool button with icon."""
        btn = TransparentToolButton(icon)
        btn.setToolTip(tooltip)
        btn.setMinimumHeight(32)
        if callback:
            btn.clicked.connect(callback)
        return btn

    @staticmethod
    def create_status_bar(layout: QVBoxLayout) -> dict:
        """Create status bar with line count and bus status."""
        status_bar = QHBoxLayout()
        line_count_label = CaptionLabel("0 lines")
        line_count_label.setStyleSheet("color: #8b949e;")
        status_bar.addWidget(line_count_label)
        status_bar.addStretch()
        bus_status_label = CaptionLabel("📡 Bus: Offline")
        bus_status_label.setStyleSheet("color: #8b949e;")
        status_bar.addWidget(bus_status_label)
        layout.addLayout(status_bar)
        return {"line_count_label": line_count_label, "bus_status_label": bus_status_label}

    @staticmethod
    def get_console_style() -> str:
        """Return console stylesheet."""
        return """
            TextEdit { background-color: #0d1117; color: #e6edf3;
                border: 1px solid #30363d; border-radius: 8px; padding: 10px;
                font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 12px; line-height: 1.5; }
            TextEdit:focus { border-color: #1f6feb; }
        """

    @staticmethod
    def save_console_to_file(console_output: TextEdit, parent, title: str = "Save Console Output") -> None:
        """Save console output to file."""
        file_path, _ = QFileDialog.getSaveFileName(parent, title, "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(console_output.toPlainText())
                InfoBar.success("Saved", f"Console saved to {file_path.split('/')[-1]}",
                                parent=parent, duration=2000)
            except Exception as e:
                InfoBar.error("Error", str(e), parent=parent, duration=3000)

    @staticmethod
    def copy_console_to_clipboard(console_output: TextEdit, parent) -> None:
        """Copy console content to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(console_output.toPlainText())
        InfoBar.success("Copied", "Console content copied to clipboard", parent=parent, duration=1500)

    @staticmethod
    def clear_console(console_output: TextEdit, parent) -> None:
        """Clear console output."""
        console_output.clear()
        InfoBar.info("Console Cleared", "All output has been cleared", parent=parent, duration=1500)
