"""
Hotkey Manager Dialog Module.
Provides dialog for managing GTT hotkeys.
"""
import subprocess
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem
from qfluentwidgets import (
    SubtitleLabel, BodyLabel, PrimaryPushButton, PushButton,
    LineEdit, InfoBar, MessageBox
)
class HotkeyManagerDialog(QWidget):
    """Dialog for managing GTT hotkeys."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⌨️ Hotkey Manager")
        self.setModal(True)
        self.setMinimumWidth(750)
        self.setMinimumHeight(550)
        self.hotkeys = []
        self.init_ui()
        self.refresh_hotkeys()
    def init_ui(self) -> None:
        """Initialize dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self._create_header(layout)
        self._create_add_section(layout)
        self._create_hotkey_list(layout)
        self._create_actions(layout)
    def _create_header(self, layout: QVBoxLayout) -> None:
        """Create dialog header."""
        title = SubtitleLabel("Global Hotkeys")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        layout.addWidget(title)
        desc = BodyLabel("Manage global hotkeys for GTT automation. Hotkeys persist across sessions.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8b949e; font-size: 13px;")
        layout.addWidget(desc)
    def _create_add_section(self, layout: QVBoxLayout) -> None:
        """Create add hotkey section."""
        add_layout = QHBoxLayout()
        add_layout.addWidget(BodyLabel("New Hotkey:"))
        self.new_hotkey_input = LineEdit()
        self.new_hotkey_input.setPlaceholderText("e.g., ctrl+alt+t")
        self.new_hotkey_input.setMaximumWidth(180)
        self.new_hotkey_input.setMinimumHeight(35)
        add_layout.addWidget(self.new_hotkey_input)
        add_layout.addWidget(BodyLabel("→"))
        self.new_hotkey_cmd_input = LineEdit()
        self.new_hotkey_cmd_input.setPlaceholderText("e.g., key ctrl+c or type Hello World")
        self.new_hotkey_cmd_input.setMinimumHeight(35)
        add_layout.addWidget(self.new_hotkey_cmd_input)
        self.add_hotkey_btn = PrimaryPushButton("Add Hotkey")
        self.add_hotkey_btn.setMinimumHeight(35)
        self.add_hotkey_btn.clicked.connect(self.add_hotkey)
        add_layout.addWidget(self.add_hotkey_btn)
        layout.addLayout(add_layout)
    def _create_hotkey_list(self, layout: QVBoxLayout) -> None:
        """Create hotkey list section."""
        layout.addWidget(BodyLabel("Registered Hotkeys:"))
        self.hotkey_list_widget = QListWidget()
        self.hotkey_list_widget.setStyleSheet(self._get_list_style())
        self.hotkey_list_widget.setMinimumHeight(350)
        layout.addWidget(self.hotkey_list_widget)
    def _get_list_style(self) -> str:
        """Return list widget stylesheet."""
        return """
            QListWidget { background-color: #1a1f26; border: 1px solid #30363d;
                border-radius: 8px; color: #e6edf3; font-size: 13px; }
            QListWidget::item { padding: 10px; border-radius: 4px; }
            QListWidget::item:selected { background-color: #1f6feb; }
        """
    def _create_actions(self, layout: QVBoxLayout) -> None:
        """Create action buttons."""
        btn_layout = QHBoxLayout()
        self.remove_hotkey_btn = PushButton("Remove Selected")
        self.remove_hotkey_btn.setMinimumHeight(35)
        self.remove_hotkey_btn.clicked.connect(self.remove_selected_hotkey)
        btn_layout.addWidget(self.remove_hotkey_btn)
        self.clear_all_btn = PushButton("Clear All")
        self.clear_all_btn.setMinimumHeight(35)
        self.clear_all_btn.setStyleSheet("color: #f85149;")
        self.clear_all_btn.clicked.connect(self.clear_all_hotkeys)
        btn_layout.addWidget(self.clear_all_btn)
        btn_layout.addStretch()
        self.refresh_btn = PushButton("🔄 Refresh")
        self.refresh_btn.setMinimumHeight(35)
        self.refresh_btn.clicked.connect(self.refresh_hotkeys)
        btn_layout.addWidget(self.refresh_btn)
        self.close_btn = PushButton("Close")
        self.close_btn.setMinimumHeight(35)
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
    def refresh_hotkeys(self) -> None:
        """Refresh hotkey list from gtt."""
        self.hotkey_list_widget.clear()
        self.hotkeys = []
        try:
            result = subprocess.run(["gtt", "--list-hotkeys"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    for line in output.split('\n'):
                        if line.strip():
                            self.hotkeys.append(line.strip())
                            self.hotkey_list_widget.addItem(QListWidgetItem(line.strip()))
                else:
                    item = QListWidgetItem("No hotkeys registered")
                    item.setStyleSheet("color: #8b949e; font-style: italic;")
                    self.hotkey_list_widget.addItem(item)
            else:
                InfoBar.warning("Error", f"Failed to list hotkeys: {result.stderr}", parent=self, duration=3000)
        except Exception as e:
            InfoBar.error("Error", str(e), parent=self, duration=3000)
    def add_hotkey(self) -> None:
        """Add a new hotkey."""
        key_combo = self.new_hotkey_input.text().strip()
        command = self.new_hotkey_cmd_input.text().strip()
        if not key_combo or not command:
            InfoBar.warning("Invalid Input", "Please enter both key combination and command", parent=self, duration=3000)
            return
        try:
            result = subprocess.run(["gtt", "--hotkey-input", f"{key_combo},{command}"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                InfoBar.success("Hotkey Added", f"Registered {key_combo} → {command}", parent=self, duration=2000)
                self.new_hotkey_input.clear()
                self.new_hotkey_cmd_input.clear()
                self.refresh_hotkeys()
            else:
                InfoBar.error("Error", f"Failed to add hotkey: {result.stderr}", parent=self, duration=4000)
        except Exception as e:
            InfoBar.error("Error", str(e), parent=self, duration=4000)
    def remove_selected_hotkey(self) -> None:
        """Remove selected hotkey."""
        current_item = self.hotkey_list_widget.currentItem()
        if not current_item:
            InfoBar.warning("No Selection", "Please select a hotkey to remove", parent=self, duration=2000)
            return
        InfoBar.info("Not Implemented", "Hotkey removal requires gtt API update", parent=self, duration=3000)
    def clear_all_hotkeys(self) -> None:
        """Clear all hotkeys."""
        msg_box = MessageBox("Clear All Hotkeys?", "This will remove all registered hotkeys. This action cannot be undone.", self)
        msg_box.yesButton.setText("Clear All")
        msg_box.cancelButton.setText("Cancel")
        if msg_box.exec():
            try:
                result = subprocess.run(["gtt", "--clear-hotkeys"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    InfoBar.success("Cleared", "All hotkeys have been removed", parent=self, duration=2000)
                    self.refresh_hotkeys()
                else:
                    InfoBar.error("Error", f"Failed to clear hotkeys: {result.stderr}", parent=self, duration=4000)
            except Exception as e:
                InfoBar.error("Error", str(e), parent=self, duration=4000)
