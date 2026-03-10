"""
Recording Controls Widget
Contains: Start/Stop buttons, recording status, timer, waveform, sensitivity, Auto VAD toggle
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Signal, Qt
from qfluentwidgets import BodyLabel, PrimaryPushButton, PushButton, ToggleButton, ComboBox

from src.circular_waveform import CircularWaveformWidget


class RecordingControlsWidget(QWidget):
    """Recording controls with waveform display"""

    # Signals
    start_clicked = Signal()
    stop_clicked = Signal()
    sensitivity_changed = Signal(str)
    auto_vad_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RecordingControlsWidget")
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # Left: Control buttons and status
        button_layout = QVBoxLayout()
        button_layout.setSpacing(8)

        # Section label
        button_label = BodyLabel("🎙️ Recording Controls")
        button_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #e6edf3;")
        button_layout.addWidget(button_label)

        # Start button
        self.listen_button = PrimaryPushButton("🎤 Start Listening")
        self.listen_button.setToolTip("Click or press F9 to start voice dictation")
        self.listen_button.clicked.connect(self._on_start_clicked)
        self.listen_button.setStyleSheet("""
            PrimaryPushButton {
                font-weight: bold;
                padding: 12px 24px;
                font-size: 14px;
                background-color: #238636;
                border-radius: 8px;
            }
            PrimaryPushButton:hover {
                background-color: #2ea043;
            }
            PrimaryPushButton:pressed {
                background-color: #196c2e;
            }
        """)
        button_layout.addWidget(self.listen_button)

        # Stop button
        self.stop_button = PushButton("⏹ Stop Listening")
        self.stop_button.setToolTip("Click or press F10 to stop recording")
        self.stop_button.clicked.connect(self._on_stop_clicked)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            PushButton {
                padding: 10px 20px;
                font-size: 13px;
                background-color: #da3633;
                color: white;
                border-radius: 8px;
            }
            PushButton:hover {
                background-color: #f85149;
            }
            PushButton:disabled {
                background-color: #30363d;
                color: #8b949e;
            }
        """)
        button_layout.addWidget(self.stop_button)

        # Recording status
        self.recording_status_label = BodyLabel("Ready")
        self.recording_status_label.setStyleSheet("color: #666666; font-size: 12px;")
        button_layout.addWidget(self.recording_status_label)

        # Recording timer
        self.recording_timer_label = BodyLabel("00:00")
        self.recording_timer_label.setStyleSheet(
            "color: #4A90E2; font-size: 14px; font-weight: bold;"
        )
        button_layout.addWidget(self.recording_timer_label)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # Center: Waveform display
        self.waveform_widget = CircularWaveformWidget()
        self.waveform_widget.setFixedSize(120, 120)
        main_layout.addWidget(self.waveform_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # Right: Sensitivity and Auto VAD
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(8)

        # Sensitivity control
        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(BodyLabel("Sensitivity:"))
        self.sensitivity_combo = ComboBox()
        self.sensitivity_combo.addItems(["Low", "Medium", "High"])
        self.sensitivity_combo.setCurrentIndex(1)  # Default to Medium
        self.sensitivity_combo.currentTextChanged.connect(self._on_sensitivity_changed)
        sensitivity_layout.addWidget(self.sensitivity_combo)
        controls_layout.addLayout(sensitivity_layout)

        # Auto VAD toggle
        self.trigger_toggle = ToggleButton("Auto VAD")
        self.trigger_toggle.setChecked(False)
        self.trigger_toggle.toggled.connect(self._on_auto_vad_toggled)
        controls_layout.addWidget(self.trigger_toggle)

        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)

        main_layout.addStretch()

    # Signal handlers
    def _on_start_clicked(self):
        """Emit start signal"""
        self.start_clicked.emit()

    def _on_stop_clicked(self):
        """Emit stop signal"""
        self.stop_clicked.emit()

    def _on_sensitivity_changed(self, text: str):
        """Emit sensitivity change signal"""
        self.sensitivity_changed.emit(text)

    def _on_auto_vad_toggled(self, checked: bool):
        """Emit Auto VAD toggle signal"""
        self.auto_vad_toggled.emit(checked)

    # Public API
    def set_listening_state(self, is_listening: bool):
        """Update UI for listening state"""
        self.listen_button.setEnabled(not is_listening)
        self.stop_button.setEnabled(is_listening)

        if is_listening:
            self.recording_status_label.setText("Listening...")
            self.recording_status_label.setStyleSheet("color: #4A90E2; font-size: 12px;")
        else:
            self.recording_status_label.setText("Ready")
            self.recording_status_label.setStyleSheet("color: #666666; font-size: 12px;")

    def set_processing_state(self, is_processing: bool):
        """Update UI for processing state"""
        if is_processing:
            self.recording_status_label.setText("Processing...")
            self.recording_status_label.setStyleSheet("color: #FF6B6B; font-size: 12px;")
            self.recording_timer_label.setText("Processing")
            self.listen_button.setEnabled(False)
            self.stop_button.setEnabled(False)
        else:
            self.listen_button.setEnabled(True)
            if not self.trigger_toggle.isChecked():
                self.stop_button.setEnabled(False)

    def update_timer(self, elapsed_seconds: float):
        """Update the recording timer display"""
        minutes = int(elapsed_seconds // 60)
        seconds = int(elapsed_seconds % 60)
        time_str = f"{minutes:02d}:{seconds:02d}"
        self.recording_timer_label.setText(time_str)

    def set_sensitivity(self, sensitivity: str):
        """Set sensitivity level"""
        index = self.sensitivity_combo.findText(sensitivity)
        if index >= 0:
            self.sensitivity_combo.setCurrentIndex(index)

    def get_sensitivity(self) -> str:
        """Get current sensitivity level"""
        return self.sensitivity_combo.currentText()

    def is_auto_vad_enabled(self) -> bool:
        """Check if Auto VAD is enabled"""
        return self.trigger_toggle.isChecked()

    def set_auto_vad_enabled(self, enabled: bool):
        """Set Auto VAD enabled state"""
        self.trigger_toggle.setChecked(enabled)
