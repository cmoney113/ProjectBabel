"""
Console Output Panel Component for GTT.
Provides real-time command execution output with filtering and search.
"""
from datetime import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import TextEdit, CaptionLabel, InfoBar
from .console_output_ui import ConsoleOutputUI


class ConsoleOutputPanel(QWidget):
    """Console output panel with filtering and search capabilities."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    def init_ui(self) -> None:
        """Initialize console panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        toolbar = QHBoxLayout()
        self._setup_toolbar(toolbar)
        layout.addLayout(toolbar)
        self.console_output = TextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet(ConsoleOutputUI.get_console_style())
        layout.addWidget(self.console_output)
        status_labels = ConsoleOutputUI.create_status_bar(layout)
        self.line_count_label = status_labels["line_count_label"]
        self.bus_status_label = status_labels["bus_status_label"]
    def _setup_toolbar(self, toolbar: QHBoxLayout) -> None:
        """Setup toolbar with buttons and controls."""
        filter_btns = ConsoleOutputUI.create_filter_buttons(toolbar)
        self.filter_info = filter_btns["filter_info"]
        self.filter_error = filter_btns["filter_error"]
        self.filter_success = filter_btns["filter_success"]
        self.filter_command = filter_btns["filter_command"]
        toolbar.addStretch()
        self.search_box = ConsoleOutputUI.create_search_box(toolbar, self.filter_console)
        self.auto_scroll_switch = ConsoleOutputUI.create_auto_scroll_toggle(toolbar)
        callbacks = {"clear": self.clear, "copy": self.copy_all, "save": self.save_to_file}
        action_btns = ConsoleOutputUI.create_action_buttons(toolbar, callbacks)
        self.clear_btn = action_btns["clear_btn"]
        self.copy_btn = action_btns["copy_btn"]
        self.save_btn = action_btns["save_btn"]
    def append(self, message: str, msg_type: str = "info") -> None:
        """Append message to console."""
        icons = {"command": "▶", "output": "  ", "error": "✗", "info": "ℹ", "success": "✓"}
        icon = icons.get(msg_type, "ℹ")
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {icon} {message}"
        self.console_output.append(formatted)
        if self.auto_scroll_switch.isChecked():
            self.console_output.verticalScrollBar().setValue(
                self.console_output.verticalScrollBar().maximum()
            )
        self._update_line_count()
    def clear(self) -> None:
        """Clear console output."""
        ConsoleOutputUI.clear_console(self.console_output, self.parent())
        self._update_line_count()
    def copy_all(self) -> None:
        """Copy all console content to clipboard."""
        ConsoleOutputUI.copy_console_to_clipboard(self.console_output, self.parent())
    def save_to_file(self) -> None:
        """Save console output to file."""
        ConsoleOutputUI.save_console_to_file(self.console_output, self.parent())
    def filter_console(self) -> None:
        """Filter console based on search text."""
        pass  # Filter console
    def _update_line_count(self) -> None:
        """Update line count label."""
        lines = self.console_output.toPlainText().split('\n')
        self.line_count_label.setText(f"{len(lines)} lines")
    def set_bus_status(self, connected: bool) -> None:
        """Update bus status indicator."""
        status = "Connected" if connected else "Offline"
        color = "#3fb950" if connected else "#8b949e"
        self.bus_status_label.setText(f"📡 Bus: {status}")
        self.bus_status_label.setStyleSheet(f"color: {color};")
