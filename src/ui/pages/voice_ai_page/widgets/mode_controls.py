"""
Mode Controls Widget
Contains: Dictation mode toggle, window selector
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import Signal
from qfluentwidgets import BodyLabel, ToggleButton, ComboBox, InfoBar


class ModeControlsWidget(QWidget):
    """Mode selection controls for Voice AI vs Dictation mode"""

    # Signals
    mode_toggled = Signal(bool)  # is_dictation_mode
    window_selected = Signal(str)  # window_id

    def __init__(self, tts_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("ModeControlsWidget")
        self.tts_manager = tts_manager
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Mode toggle
        self.mode_toggle = ToggleButton("Dictation Mode", self)
        self.mode_toggle.setChecked(False)
        self.mode_toggle.toggled.connect(self._on_mode_toggled)
        layout.addWidget(BodyLabel("Mode:"))
        layout.addWidget(self.mode_toggle)

        # Window selector for dictation mode
        window_label = BodyLabel("Window:")
        window_label.setStyleSheet(
            "font-size: 12px; color: #888888; margin-left: 20px;"
        )
        layout.addWidget(window_label)

        self.window_combo = ComboBox()
        self.window_combo.setFixedWidth(200)
        self.window_combo.setEnabled(False)
        self.window_combo.addItem("Select window...", userData=None)
        self.window_combo.currentIndexChanged.connect(self._on_window_changed)
        layout.addWidget(self.window_combo)

        layout.addStretch()

    # Signal handlers
    def _on_mode_toggled(self, checked: bool):
        """Handle mode toggle"""
        if checked:
            self._populate_window_list()
            self.window_combo.setEnabled(True)
            InfoBar.success(
                "Dictation Mode",
                "Select a target window for dictation injection",
                parent=self,
                duration=2000,
            )
        else:
            self.window_combo.setEnabled(False)
            InfoBar.info(
                "Voice AI Mode",
                "Using conversational AI with context awareness",
                parent=self,
                duration=2000,
            )

        self.mode_toggled.emit(checked)

    def _on_window_changed(self, index: int):
        """Handle window selection change"""
        window_id = self.window_combo.currentData()
        if window_id:
            InfoBar.info(
                "Window Selected",
                f"Dictation will be injected to window ID: {window_id}",
                parent=self,
                duration=1500,
            )
            self.window_selected.emit(window_id)

    # Private methods
    def _populate_window_list(self):
        """Populate window combo with open windows from gtt --list"""
        windows = self.tts_manager.get_window_list()

        self.window_combo.blockSignals(True)
        self.window_combo.clear()

        if not windows:
            self.window_combo.addItem("No windows found", userData=None)
            InfoBar.warning(
                "No Windows",
                "No open windows found via gtt",
                parent=self,
                duration=2000,
            )
        else:
            self.window_combo.addItem("Select window...", userData=None)
            for w in windows:
                title = w.get("title", "Unknown")[:50]
                wm_class = w.get("wm_class", "")
                display_text = f"{title} ({wm_class})" if wm_class else title
                self.window_combo.addItem(display_text, userData=w.get("id"))

        self.window_combo.blockSignals(False)

    # Public API
    def is_dictation_mode(self) -> bool:
        """Check if dictation mode is enabled"""
        return self.mode_toggle.isChecked()

    def set_dictation_mode(self, enabled: bool):
        """Set dictation mode enabled state"""
        self.mode_toggle.setChecked(enabled)
        if enabled:
            self._populate_window_list()
            self.window_combo.setEnabled(True)
        else:
            self.window_combo.setEnabled(False)

    def get_selected_window_id(self) -> str | None:
        """Get selected window ID for dictation"""
        if self.is_dictation_mode():
            return self.window_combo.currentData()
        return None

    def set_selected_window_id(self, window_id: str | None):
        """Set selected window ID"""
        if window_id:
            for i in range(self.window_combo.count()):
                if self.window_combo.itemData(i) == window_id:
                    self.window_combo.setCurrentIndex(i)
                    break
