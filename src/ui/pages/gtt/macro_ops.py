"""
GTT Page Macro Operations Mixin.
Provides macro execution methods for GTTPage.
"""

from typing import List


class MacroOperationsMixin:
    """Mixin for macro execution operations."""

    MACROS = {
        "focus_hyper": ["gtt", "--launch", "Hyper"],
        "focus_vscode": ["gtt", "--focus", "Visual Studio Code"],
        "focus_browser": ["gtt", "--focus", "Firefox"],
        "type_hello": ["gtt", "--type", "Hello from GTT!"],
        "copy_paste": ["gtt", "--key", "ctrl+c", "--key", "ctrl+v"],
        "new_terminal": ["gtt", "--launch", "Hyper"],
        "screenshot": ["gtt", "--sc", "/tmp/screenshot.png"],
        "maximize_window": ["gtt", "--maximize", "active"],
        "ocr_active": ["gtt", "--ocr"],
        "clipboard_get": ["gtt", "--cb"],
    }

    def execute_macro(self, macro_id: str) -> None:
        """Execute pre-loaded macro by ID."""
        if macro_id in self.MACROS:
            self.execute_gtt_command(self.MACROS[macro_id])
            self.center_panel.console_panel.append(f"Executed macro: {macro_id}", "info")

    def get_macro_commands(self) -> List[str]:
        """Get list of available macro IDs."""
        return list(self.MACROS.keys())
