"""
GTT Page Window Management Mixin.
Provides window listing and manipulation methods for GTTPage.
"""

import json
import subprocess
from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem
from qfluentwidgets import InfoBar


class WindowManagementMixin:
    """Mixin for window management operations."""

    def refresh_windows(self) -> None:
        """Refresh window list from GTT daemon."""
        try:
            result = subprocess.run(
                ["gtt", "--list", "--format", "json"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self.window_list = json.loads(result.stdout)
                self._update_window_list_ui()
                self.center_panel.script_builder.window_list = self.window_list
                InfoBar.success("Windows Refreshed", f"Found {len(self.window_list)} windows",
                                parent=self, duration=2000)
        except Exception as e:
            InfoBar.error("Error", str(e), parent=self, duration=3000)

    def _update_window_list_ui(self) -> None:
        """Update window list widget UI."""
        self.left_panel.window_list_widget.clear()
        for window in self.window_list:
            title = window.get("title", "Untitled")[:50]
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, window.get("id"))
            self.left_panel.window_list_widget.addItem(item)

    def get_selected_window_id(self) -> Optional[str]:
        """Get selected window ID."""
        current = self.left_panel.window_list_widget.currentItem()
        return current.data(Qt.UserRole) if current else None

    def focus_selected_window(self) -> None:
        """Focus selected window."""
        window_id = self.get_selected_window_id()
        if window_id:
            self.execute_gtt_command(["gtt", "--focus", str(window_id)])
            self.center_panel.console_panel.append(f"Focused window {window_id}", "success")
        else:
            InfoBar.warning("No Selection", "Please select a window", parent=self, duration=2000)

    def close_selected_window(self) -> None:
        """Close selected window."""
        window_id = self.get_selected_window_id()
        if window_id:
            self.execute_gtt_command(["gtt", "--close", str(window_id)])
            self.center_panel.console_panel.append(f"Closed window {window_id}", "success")
            self.refresh_windows()
        else:
            InfoBar.warning("No Selection", "Please select a window", parent=self, duration=2000)

    def minimize_selected_window(self) -> None:
        """Minimize selected window."""
        window_id = self.get_selected_window_id()
        if window_id:
            self.execute_gtt_command(["gtt", "--minimize", str(window_id)])
            self.center_panel.console_panel.append(f"Minimized window {window_id}", "success")

    def maximize_selected_window(self) -> None:
        """Maximize selected window."""
        window_id = self.get_selected_window_id()
        if window_id:
            self.execute_gtt_command(["gtt", "--maximize", str(window_id)])
            self.center_panel.console_panel.append(f"Maximized window {window_id}", "success")

    def unmaximize_selected_window(self) -> None:
        """Unmaximize selected window."""
        window_id = self.get_selected_window_id()
        if window_id:
            self.execute_gtt_command(["gtt", "--unmaximize", str(window_id)])
            self.center_panel.console_panel.append(f"Unmaximized window {window_id}", "success")
