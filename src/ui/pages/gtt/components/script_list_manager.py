"""
Script Builder List Manager.
Handles script command list operations and persistence.
"""

import json
from typing import List, Dict, Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QFileDialog
from qfluentwidgets import InfoBar


class ScriptListManager:
    """Manages script command list widget and persistence operations."""

    def __init__(self, list_widget: QListWidget):
        self.list_widget = list_widget
        self.script_commands: List[Dict[str, Any]] = []

    def add_command(self, cmd_data: Dict[str, Any]) -> None:
        """Add command to list and internal storage."""
        self.script_commands.append(cmd_data)
        self._add_to_list(cmd_data)

    def _add_to_list(self, cmd_data: Dict[str, Any]) -> None:
        """Add command item to list widget."""
        params = cmd_data.get("params", {})
        if params:
            params_str = ", ".join(f"{k}={v}" for k, v in params.items())
            item_text = f"{cmd_data['type']} ({params_str})"
        else:
            item_text = cmd_data['type']
        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, len(self.script_commands) - 1)
        self.list_widget.addItem(item)

    def remove_selected(self) -> bool:
        """Remove selected command. Returns True if removed."""
        current = self.list_widget.currentItem()
        if not current:
            return False
        index = current.data(Qt.UserRole)
        if 0 <= index < len(self.script_commands):
            self.script_commands.pop(index)
            self.list_widget.takeItem(self.list_widget.row(current))
            for i in range(self.list_widget.count()):
                self.list_widget.item(i).setData(Qt.UserRole, i)
            return True
        return False

    def clear(self) -> None:
        """Clear all commands."""
        self.script_commands = []
        self.list_widget.clear()

    def get_commands(self) -> List[Dict[str, Any]]:
        """Get all script commands."""
        return self.script_commands.copy()

    def is_empty(self) -> bool:
        """Check if script is empty."""
        return len(self.script_commands) == 0

    def export_script(self, parent=None) -> bool:
        """Export script to JSON file."""
        if self.is_empty():
            InfoBar.warning("Empty Script", "No commands to export", parent=parent, duration=2000)
            return False
        file_path, _ = QFileDialog.getSaveFileName(
            parent, "Save GTT Script", "",
            "GTT Script Files (*.gtt.json);;JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return False
        try:
            export_data = {
                "version": "1.0",
                "name": file_path.split("/")[-1].replace(".gtt.json", ""),
                "commands": self.script_commands,
                "command_count": len(self.script_commands)
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            InfoBar.success("Export Successful", f"Saved {len(self.script_commands)} commands",
                            parent=parent, duration=3000)
            return True
        except Exception as e:
            InfoBar.error("Export Failed", str(e), parent=parent, duration=4000)
            return False

    def import_script(self, parent=None) -> bool:
        """Import script from JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            parent, "Load GTT Script", "",
            "GTT Script Files (*.gtt.json);;JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return False
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            if "commands" not in import_data:
                raise ValueError("Invalid format")
            self.clear()
            for cmd in import_data["commands"]:
                self.add_command(cmd)
            InfoBar.success("Import Successful", f"Loaded {len(self.script_commands)} commands",
                            parent=parent, duration=3000)
            return True
        except Exception as e:
            InfoBar.error("Import Failed", str(e), parent=parent, duration=4000)
            return False
