"""
Window Manager Service for GTT.
Handles window listing, focusing, and management operations via gtt CLI.
"""

import json
import subprocess
from typing import List, Dict, Any, Optional


class WindowManagerService:
    """Service for managing windows via GTT daemon."""

    def __init__(self):
        """Initialize window manager service."""
        self.window_list: List[Dict[str, Any]] = []

    def refresh_windows(self) -> List[Dict[str, Any]]:
        """
        Refresh the window list from GTT daemon.
        
        Returns:
            List of window dictionaries with id, title, etc.
        """
        try:
            result = subprocess.run(
                ["gtt", "--list", "--format", "json"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                self.window_list = json.loads(result.stdout)
                return self.window_list
        except Exception:
            pass
        self.window_list = []
        return []

    def get_window_by_id(self, window_id: str) -> Optional[Dict[str, Any]]:
        """
        Get window data by ID.
        
        Args:
            window_id: The window ID to find
        
        Returns:
            Window dict if found, None otherwise
        """
        for window in self.window_list:
            if window.get("id") == window_id:
                return window
        return None

    def focus_window(self, window_id: str) -> bool:
        """Focus a window by ID."""
        try:
            result = subprocess.run(
                ["gtt", "--focus", str(window_id)],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def close_window(self, window_id: str) -> bool:
        """Close a window by ID."""
        try:
            result = subprocess.run(
                ["gtt", "--close", str(window_id)],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def maximize_window(self, window_id: str) -> bool:
        """Maximize a window by ID."""
        try:
            result = subprocess.run(
                ["gtt", "--maximize", str(window_id)],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def minimize_window(self, window_id: str) -> bool:
        """Minimize a window by ID."""
        try:
            result = subprocess.run(
                ["gtt", "--minimize", str(window_id)],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def unmaximize_window(self, window_id: str) -> bool:
        """Unmaximize a window by ID."""
        try:
            result = subprocess.run(
                ["gtt", "--unmaximize", str(window_id)],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def launch_app(self, app_name: str) -> bool:
        """Launch an application by name."""
        try:
            result = subprocess.run(
                ["gtt", "--launch", app_name],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
