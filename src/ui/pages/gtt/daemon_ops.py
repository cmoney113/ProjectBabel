"""
GTT Page Daemon Management Mixin.
Provides GTT daemon startup and management methods for GTTPage.
"""

import subprocess
from PySide6.QtCore import QTimer
from qfluentwidgets import InfoBar
from .startup import GTTStartupThread


class DaemonManagementMixin:
    """Mixin for GTT daemon management operations."""

    def check_gtt_status(self) -> None:
        """Check GTT daemon status."""
        try:
            result = subprocess.run(["pgrep", "-f", "gttd"], capture_output=True, text=True, timeout=2)
            self.gtt_running = result.returncode == 0
            self.update_gtt_status_ui()
        except Exception:
            self.gtt_running = False
            self.update_gtt_status_ui()

    def update_gtt_status_ui(self) -> None:
        """Update status UI based on daemon state."""
        if self.gtt_running:
            self.left_panel.status_label.setText("Running")
            self.left_panel.status_label.setStyleSheet("color: #3fb950; font-weight: bold;")
            self.left_panel.status_indicator.setVisible(False)
            self.left_panel.start_gtt_btn.setText("⏹ Stop GTT")
            self.left_panel.start_gtt_btn.setStyleSheet(
                "PrimaryPushButton { background-color: #da3633; color: white; }"
            )
        else:
            self.left_panel.status_label.setText("Not Running")
            self.left_panel.status_label.setStyleSheet("color: #8b949e;")
            self.left_panel.status_indicator.setVisible(True)

    def start_gtt_daemon(self) -> None:
        """Start GTT daemon."""
        if self.gtt_running:
            self.stop_gtt_daemon()
            return
        self.left_panel.startup_progress.setVisible(True)
        self.left_panel.start_gtt_btn.setEnabled(False)
        self.startup_thread = GTTStartupThread()
        self.startup_thread.status_signal.connect(self.on_gtt_startup_status)
        self.startup_thread.completed_signal.connect(self.on_gtt_startup_complete)
        self.startup_thread.start()

    def stop_gtt_daemon(self) -> None:
        """Stop GTT daemon."""
        try:
            subprocess.run(["pkill", "-f", "gttd"], capture_output=True, timeout=2)
            subprocess.run(["pkill", "-f", "gtt-portal"], capture_output=True, timeout=2)
            self.gtt_running = False
            self.update_gtt_status_ui()
            self.center_panel.console_panel.append("GTT daemon stopped", "info")
            InfoBar.info("GTT Stopped", "Daemon has been stopped", parent=self, duration=2000)
        except Exception as e:
            InfoBar.error("Error", str(e), parent=self, duration=3000)

    def on_gtt_startup_status(self, title: str, message: str) -> None:
        """Handle startup status update."""
        self.left_panel.status_label.setText(message)
        self.center_panel.console_panel.append(f"[Startup] {message}", "info")

    def on_gtt_startup_complete(self, success: bool) -> None:
        """Handle startup completion."""
        self.left_panel.startup_progress.setVisible(False)
        self.left_panel.start_gtt_btn.setEnabled(True)
        if success:
            self.gtt_running = True
            self.update_gtt_status_ui()
            InfoBar.success("GTT Started", "Daemon is ready", parent=self, duration=3000)
            self.refresh_windows()
        else:
            InfoBar.error("Startup Failed", "Could not start daemon", parent=self, duration=3000)
