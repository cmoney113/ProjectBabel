"""
Mini Mode Page - Compact dictation-focused UI for overlay mode
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    SubtitleLabel,
    BodyLabel,
    PrimaryPushButton,
    ToggleButton,
    ComboBox,
    CardWidget,
    TransparentToolButton,
    FluentIcon,
)
from src.circular_waveform import CircularWaveformWidget


class MiniModePage:
    """Compact page for mini-mode overlay"""

    def __init__(self, main_window):
        self.main_window = main_window
        self.tts_manager = main_window.tts_manager
        self.settings_manager = main_window.settings_manager
        self.dialog = None
        self.is_listening = False

    def create_dialog(self, parent):
        """Create mini-mode as a frameless dialog"""
        dialog = QDialog(parent)
        dialog.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        dialog.setModal(False)
        dialog.resize(500, 350)

        card = CardWidget(dialog)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        header = QHBoxLayout()
        title = SubtitleLabel("Voice AI")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header.addWidget(title)
        header.addStretch()

        exit_btn = TransparentToolButton(FluentIcon.UNPIN, dialog)
        exit_btn.setToolTip("Exit Mini Mode")
        exit_btn.clicked.connect(self._on_exit_clicked)
        header.addWidget(exit_btn)

        card_layout.addLayout(header)

        self.waveform = CircularWaveformWidget()
        self.waveform.setFixedSize(80, 80)
        card_layout.addWidget(self.waveform, alignment=Qt.AlignmentFlag.AlignCenter)

        self.listen_button = PrimaryPushButton("Listen", dialog)
        self.listen_button.setFixedHeight(45)
        self.listen_button.clicked.connect(self._on_listen_clicked)
        card_layout.addWidget(self.listen_button)

        self.status_label = BodyLabel("Ready")
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.status_label)

        window_layout = QHBoxLayout()
        window_layout.addWidget(BodyLabel("Target:"))

        self.window_combo = ComboBox()
        self.window_combo.setFixedWidth(180)
        self._populate_windows()
        window_layout.addWidget(self.window_combo)
        window_layout.addStretch()

        card_layout.addLayout(window_layout)

        # KittenTTS voice selection
        voice_layout = QHBoxLayout()
        voice_layout.addWidget(BodyLabel("Voice:"))
        
        self.kittentts_voice_combo = ComboBox()
        self.kittentts_voice_combo.addItems(["Bella", "Jasper", "Luna", "Bruno", "Rosie", "Hugo", "Kiki", "Leo"])
        self.kittentts_voice_combo.setFixedWidth(120)
        self.kittentts_voice_combo.setCurrentIndex(1)  # Default to Jasper
        voice_layout.addWidget(self.kittentts_voice_combo)
        voice_layout.addStretch()
        
        # Initially hide unless KittenTTS is selected
        self.kittentts_voice_combo.setVisible(False)
        
        card_layout.addLayout(voice_layout)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(BodyLabel("Mode:"))

        self.mode_toggle = ToggleButton("Dictation", dialog)
        self.mode_toggle.setFixedWidth(100)
        self.mode_toggle.toggled.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_toggle)

        # KittenTTS voice selection
        voice_layout = QHBoxLayout()
        voice_layout.addWidget(BodyLabel("Voice:"))

        self.kittentts_voice_combo = ComboBox()
        self.kittentts_voice_combo.addItems(["Bella", "Jasper", "Luna", "Bruno", "Rosie", "Hugo", "Kiki", "Leo"])
        self.kittentts_voice_combo.setFixedWidth(120)
        self.kittentts_voice_combo.setCurrentIndex(1)  # Default to Jasper
        voice_layout.addWidget(self.kittentts_voice_combo)
        voice_layout.addStretch()

        card_layout.addLayout(voice_layout)

        wakeword_btn = ToggleButton("Wake", dialog)
        wakeword_btn.setFixedWidth(60)
        wakeword_btn.setToolTip("Enable wake word detection")
        wakeword_btn.toggled.connect(
            lambda checked: self._on_wakeword_toggled(checked, wakeword_btn)
        )
        mode_layout.addWidget(wakeword_btn)

        mode_layout.addStretch()

        card_layout.addLayout(mode_layout)

        self.dialog = dialog
        self.wakeword_button = wakeword_btn
        return dialog

    def create_widget(self, parent):
        return self.create_dialog(parent)

    def _populate_windows(self):
        windows = self.tts_manager.get_window_list()

        self.window_combo.clear()
        self.window_combo.addItem("Auto-inject", userData=None)

        if windows:
            for w in windows:
                title = w.get("title", "Unknown")[:30]
                self.window_combo.addItem(title, userData=w.get("id"))

    def _on_exit_clicked(self):
        self.main_window.stop_wakeword_listening()
        self.main_window.exit_mini_mode()

    def _on_mode_changed(self, checked):
        if self.wakeword_button.isChecked():
            is_dictation = self.mode_toggle.isChecked()
            self.main_window.start_wakeword_listening(is_dictation)

    def _on_wakeword_toggled(self, checked, button):
        if checked:
            is_dictation = self.mode_toggle.isChecked()
            self.main_window.start_wakeword_listening(is_dictation)
            button.setText("ON")
            self.status_label.setText(f"Listening for wake word...")
        else:
            self.main_window.stop_wakeword_listening()
            button.setText("Wake")
            self.status_label.setText("Ready")

    def on_wakeword_detected(self):
        """Called when wake word is detected"""
        self.status_label.setText("Wake word detected!")
        self.status_label.setStyleSheet(
            "color: #4A90E2; font-size: 12px; font-weight: bold;"
        )
        if not self.is_listening:
            self._start_listening()

    def on_wakeword_error(self, error_msg):
        """Called when wake word has an error"""
        self.wakeword_button.setChecked(False)
        self.wakeword_button.setText("Wake")
        self.status_label.setText(f"Wake error: {error_msg[:30]}")
        self.status_label.setStyleSheet("color: #FF6B6B; font-size: 12px;")

    def _on_listen_clicked(self):
        if self.listen_button.text() == "Listen":
            self._start_listening()
        else:
            self._stop_listening()

    def _start_listening(self):
        if self.is_listening:
            return
        self.is_listening = True
        self.listen_button.setText("Stop")
        self.status_label.setText("Listening...")
        self.status_label.setStyleSheet("color: #4A90E2; font-size: 12px;")

        if hasattr(self.main_window.voice_ai_page, "voice_processor"):
            vp = self.main_window.voice_ai_page.voice_processor
            vp.start_recording()

    def _stop_listening(self):
        if not self.is_listening:
            return
        self.is_listening = False
        self.listen_button.setEnabled(False)
        self.status_label.setText("Processing...")

        if hasattr(self.main_window.voice_ai_page, "voice_processor"):
            vp = self.main_window.voice_ai_page.voice_processor
            audio_data = vp.stop_recording()

            if audio_data is not None and len(audio_data) > 0:
                is_dictation = self.mode_toggle.isChecked()

                # Auto-select second-to-last window for dictation (skip mini-mode window)
                window_id = None
                if is_dictation:
                    windows = self.tts_manager.get_window_list()
                    if len(windows) >= 2:
                        window_id = windows[1].get("id")  # Second window
                        self.status_label.setText(
                            f"Targeting: {windows[1].get('title', '')[:25]}..."
                        )

                worker = self.main_window.voice_worker
                worker.set_audio(audio_data)
                worker.set_dictation_mode(is_dictation)
                worker.set_dictation_window(window_id)
                worker.set_verbosity("balanced")
                worker.start()
            else:
                self._reset_listen_state()

    def _reset_listen_state(self):
        self.is_listening = False
        self.listen_button.setText("Listen")
        self.listen_button.setEnabled(True)
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")

    def on_processing_started(self):
        self.listen_button.setEnabled(False)

    def on_processing_finished(self):
        self._reset_listen_state()

    def on_transcription_ready(self, text):
        self.status_label.setText(f"Got: {text[:30]}...")

    def on_response_ready(self, text):
        self.status_label.setText("Done!")
