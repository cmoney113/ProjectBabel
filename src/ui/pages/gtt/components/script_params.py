"""
Script Builder Parameter Helpers.
Provides parameter input builders for different GTT command types.
"""

from typing import Any, Dict, Optional
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget
from qfluentwidgets import BodyLabel, ComboBox, LineEdit, QSpinBox, CaptionLabel


class ParamBuilderMixin:
    """Mixin providing parameter building methods for script builder."""

    def clear_params_layout(self) -> None:
        """Clear all widgets from params layout."""
        while self.params_layout.count():
            child = self.params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def build_window_selector(self) -> None:
        """Add window selector for window operations."""
        self.params_layout.addWidget(BodyLabel("Select Window:"))
        self.param_window_combo = ComboBox()
        self.param_window_combo.setMinimumHeight(35)
        for window in self.window_list:
            title = window.get("title", "Untitled")[:50]
            self.param_window_combo.addItem(title, userData=window.get("id"))
        self.params_layout.addWidget(self.param_window_combo)

    def build_move_params(self) -> None:
        """Add X/Y coordinate inputs for Move Window."""
        self.build_window_selector()
        coords = QHBoxLayout()
        coords.addWidget(BodyLabel("X:"))
        self.param_move_x = LineEdit()
        self.param_move_x.setPlaceholderText("e.g., 100 or 0.5")
        self.param_move_x.setMinimumHeight(35)
        coords.addWidget(self.param_move_x)
        coords.addWidget(BodyLabel("Y:"))
        self.param_move_y = LineEdit()
        self.param_move_y.setPlaceholderText("e.g., 200 or 0.3")
        self.param_move_y.setMinimumHeight(35)
        coords.addWidget(self.param_move_y)
        self.params_layout.addLayout(coords)

    def build_resize_params(self) -> None:
        """Add width/height inputs for Resize Window."""
        self.build_window_selector()
        dims = QHBoxLayout()
        dims.addWidget(BodyLabel("Width:"))
        self.param_resize_w = LineEdit()
        self.param_resize_w.setPlaceholderText("e.g., 800 or 0.5")
        self.param_resize_w.setMinimumHeight(35)
        dims.addWidget(self.param_resize_w)
        dims.addWidget(BodyLabel("Height:"))
        self.param_resize_h = LineEdit()
        self.param_resize_h.setPlaceholderText("e.g., 600 or 0.7")
        self.param_resize_h.setMinimumHeight(35)
        dims.addWidget(self.param_resize_h)
        self.params_layout.addLayout(dims)

    def build_launch_params(self) -> None:
        """Add app name input for Launch App."""
        self.params_layout.addWidget(BodyLabel("App Name:"))
        self.param_app_name = LineEdit()
        self.param_app_name.setPlaceholderText("e.g., Firefox, Visual Studio Code")
        self.param_app_name.setMinimumHeight(35)
        self.params_layout.addWidget(self.param_app_name)

    def build_text_params(self) -> None:
        """Add text input for Type Text."""
        self.params_layout.addWidget(BodyLabel("Text:"))
        self.param_text = LineEdit()
        self.param_text.setPlaceholderText("Enter text to type")
        self.param_text.setMinimumHeight(35)
        self.params_layout.addWidget(self.param_text)

    def build_keys_params(self) -> None:
        """Add key combination input for Send Keys."""
        self.params_layout.addWidget(BodyLabel("Key Combination:"))
        self.param_keys = LineEdit()
        self.param_keys.setPlaceholderText("e.g., ctrl+c, super+Enter")
        self.param_keys.setMinimumHeight(35)
        self.params_layout.addWidget(self.param_keys)

    def build_screenshot_params(self) -> None:
        """Add path input for Screenshot."""
        self.params_layout.addWidget(BodyLabel("Save Path:"))
        self.param_screenshot_path = LineEdit()
        self.param_screenshot_path.setText("/tmp/screenshot.png")
        self.param_screenshot_path.setMinimumHeight(35)
        self.params_layout.addWidget(self.param_screenshot_path)

    def build_wait_params(self) -> None:
        """Add duration spinbox for Wait."""
        self.params_layout.addWidget(BodyLabel("Duration (ms):"))
        self.param_wait = QSpinBox()
        self.param_wait.setMaximum(60000)
        self.param_wait.setValue(1000)
        self.param_wait.setMinimumHeight(35)
        self.params_layout.addWidget(self.param_wait)

    def build_termpipe_params(self) -> None:
        """Add shell command input for TermPipe."""
        self.params_layout.addWidget(BodyLabel("Shell Command:"))
        self.param_termpipe = LineEdit()
        self.param_termpipe.setPlaceholderText("e.g., ls -la ~/projects")
        self.param_termpipe.setMinimumHeight(35)
        self.params_layout.addWidget(self.param_termpipe)
        info = CaptionLabel("💡 Powered by TermPipe (MiniMax-M2.1)")
        info.setStyleSheet("color: #4A90E2;")
        self.params_layout.addWidget(info)

    def get_param_value(self, attr_name: str, default: Any = None) -> Any:
        """Safely get parameter value from dynamic attribute."""
        if hasattr(self, attr_name):
            widget = getattr(self, attr_name)
            if hasattr(widget, 'text'):
                return widget.text()
            elif hasattr(widget, 'currentData'):
                return widget.currentData()
            elif hasattr(widget, 'value'):
                return widget.value()
        return default

    def collect_params(self) -> Dict[str, Any]:
        """Collect all parameter values into dict."""
        params = {}
        param_map = {
            'window_id': 'param_window_combo',
            'app_name': 'param_app_name',
            'text': 'param_text',
            'keys': 'param_keys',
            'x': 'param_move_x',
            'y': 'param_move_y',
            'w': 'param_resize_w',
            'h': 'param_resize_h',
            'path': 'param_screenshot_path',
            'duration': 'param_wait',
            'command': 'param_termpipe',
        }
        for key, attr in param_map.items():
            value = self.get_param_value(attr)
            if value is not None:
                params[key] = value
        return params
