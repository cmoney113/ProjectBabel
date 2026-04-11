"""
GTT Startup Thread Module.
Handles background daemon initialization with modal auto-acceptance.
"""

import subprocess
from PySide6.QtCore import Signal, QThread, QTimer


class GTTStartupThread(QThread):
    """Background thread for GTT daemon startup sequence."""

    status_signal = Signal(str, str)  # title, message
    completed_signal = Signal(bool)   # success

    def __init__(self):
        super().__init__()
        self.portal_process = None

    def run(self) -> None:
        """Execute GTT startup sequence with modal auto-acceptance."""
        try:
            self.status_signal.emit("Starting GTT Portal", "Launching Remote Desktop portal...")
            self.portal_process = subprocess.Popen(
                ["gtt-portal"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.status_signal.emit("Accepting Permission", "Auto-accepting Wayland RD modal...")
            QTimer.singleShot(40, self.accept_modal)
            self.msleep(150)

            self.status_signal.emit("Starting Daemon", "Launching gttuni daemon...")
            result = subprocess.run(["gttuni", "--daemon"], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                self.status_signal.emit("GTT Ready", "Daemon started successfully")
                self.completed_signal.emit(True)
            else:
                self.status_signal.emit("Daemon Error", result.stderr or "Unknown error")
                self.completed_signal.emit(False)
        except subprocess.TimeoutExpired:
            self.status_signal.emit("Startup Timeout", "Process timed out")
            self.completed_signal.emit(False)
        except Exception as e:
            self.status_signal.emit("Startup Failed", str(e))
            self.completed_signal.emit(False)

    def accept_modal(self) -> None:
        """Execute uinput key sequence to accept RD modal."""
        try:
            subprocess.run(
                'echo "key space,,pause 15,,tab,,tab,,space" | wbind',
                shell=True, capture_output=True, timeout=2
            )
        except Exception as e:
            self.status_signal.emit("Modal Acceptance Failed", str(e))
