"""
Voice AI Page - Main voice processing interface
Contains recording controls, waveform display, model selections, and response displays
"""

import time
import re
import logging
from PySide6.QtCore import Qt, Signal, Slot
from src.model_registry import ModelRegistry

logger = logging.getLogger(__name__)
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    SubtitleLabel,
    BodyLabel,
    TitleLabel,
    PushButton,
    PrimaryPushButton,
    ComboBox,
    LineEdit,
    ToggleButton,
    SwitchButton,
    CardWidget,
    TextEdit,
    IndeterminateProgressRing,
    InfoBar,
)
from src.circular_waveform import CircularWaveformWidget
from src.markdown_display import ScrollableMarkdownDisplay


class VoiceAIPage(QWidget):
    """Main voice AI processing page with recording controls and displays"""

    # Signals for communication with main window
    start_listening_requested = Signal()
    stop_listening_requested = Signal()
    manual_activation_requested = Signal()

    def __init__(self, main_window):
        super().__init__()
        self.setObjectName("VoiceAIPage")
        self.main_window = main_window
        self.current_verbosity = "balanced"
        self.current_target_language = "en"
        self.translation_enabled = False
        self.recording_start_time = 0

        # Get references to managers
        self.settings_manager = main_window.get_settings_manager()
        self.chat_session_manager = main_window.get_chat_session_manager()
        self.voice_processor = main_window.get_voice_processor()
        self.tts_manager = main_window.get_tts_manager()

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Initialize the user interface"""
        # Main horizontal layout: sidebar + content
        page_layout = QHBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # Create sidebar
        from src.chat_sidebar import ChatSidebar

        self.chat_sidebar = ChatSidebar(self.chat_session_manager)
        self.chat_sidebar.session_selected.connect(self._on_session_selected)
        self.chat_sidebar.new_chat_requested.connect(self._on_new_chat)
        page_layout.addWidget(self.chat_sidebar)

        # Vertical layout for main content
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        title = SubtitleLabel("Canary Voice AI Assistant")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(title)

        # Mini mode button
        from qfluentwidgets import TransparentToolButton, FluentIcon

        self.mini_mode_button = TransparentToolButton(FluentIcon.PIN, self)
        self.mini_mode_button.setToolTip("Toggle Mini Mode")
        self.mini_mode_button.clicked.connect(self._toggle_mini_mode)
        header_layout.addWidget(self.mini_mode_button)

        header_layout.addStretch()
        content_layout.addLayout(header_layout)

        # Recording controls and waveform
        recording_layout = QHBoxLayout()

        # Control buttons - RECORDING section
        button_layout = QVBoxLayout()
        button_label = BodyLabel("🎙️ Recording Controls")
        button_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #e6edf3;")
        button_layout.addWidget(button_label)
        
        self.listen_button = PrimaryPushButton("🎤 Start Listening")
        self.listen_button.setToolTip("Click or press F9 to start voice dictation")
        self.listen_button.clicked.connect(self.start_listening)
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
        
        self.stop_button = PushButton("⏹ Stop Listening")
        self.stop_button.setToolTip("Click or press F10 to stop recording")
        self.stop_button.clicked.connect(self.stop_listening)
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
        
        button_layout.addWidget(self.listen_button)
        button_layout.addWidget(self.stop_button)

        # Recording status
        self.recording_status_label = BodyLabel("Ready")
        self.recording_status_label.setStyleSheet("color: #666666; font-size: 12px;")
        self.recording_timer_label = BodyLabel("00:00")
        self.recording_timer_label.setStyleSheet(
            "color: #4A90E2; font-size: 14px; font-weight: bold;"
        )

        status_layout = QVBoxLayout()
        status_layout.addWidget(self.recording_status_label)
        status_layout.addWidget(self.recording_timer_label)

        button_layout.addLayout(status_layout)
        button_layout.addStretch()

        # Circular waveform display
        self.waveform_widget = CircularWaveformWidget()
        self.waveform_widget.setFixedSize(120, 120)

        # Sensitivity control
        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(BodyLabel("Sensitivity:"))
        self.sensitivity_combo = ComboBox()
        self.sensitivity_combo.addItems(["Low", "Medium", "High"])
        self.sensitivity_combo.setCurrentIndex(1)  # Default to Medium
        sensitivity_layout.addWidget(self.sensitivity_combo)

        sensitivity_layout.addSpacing(20)

        # Auto VAD toggle
        self.trigger_toggle = ToggleButton("Auto VAD")
        self.trigger_toggle.setChecked(False)
        sensitivity_layout.addWidget(self.trigger_toggle)

        sensitivity_layout.addStretch()

        waveform_layout = QVBoxLayout()
        waveform_layout.addWidget(
            self.waveform_widget, alignment=Qt.AlignmentFlag.AlignCenter
        )
        waveform_layout.addLayout(sensitivity_layout)

        # Combine layouts
        recording_layout.addLayout(button_layout)
        recording_layout.addLayout(waveform_layout)
        recording_layout.addStretch()

        content_layout.addLayout(recording_layout)

        # ASR Model selection - SPEECH TO TEXT
        asr_layout = QHBoxLayout()
        asr_label = BodyLabel("🎯 ASR Model (Speech→Text):")
        asr_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #e6edf3;")
        asr_layout.addWidget(asr_label)
        self.asr_model_combo = ComboBox()
        self.asr_model_combo.setToolTip("Select speech recognition model. Models: Canary (accurate), Parakeet (fast), SenseVoice (multilingual)")
        asr_models = self.voice_processor.get_available_asr_models()
        for model_id, model_name in asr_models.items():
            self.asr_model_combo.addItem(model_name, userData=model_id)
        # Set current model
        current_asr = self.voice_processor.get_current_asr_model()
        index = self.asr_model_combo.findData(current_asr)
        if index >= 0:
            self.asr_model_combo.setCurrentIndex(index)
        asr_layout.addWidget(self.asr_model_combo)
        asr_layout.addStretch()
        content_layout.addLayout(asr_layout)

        # TTS Model selection - TEXT TO SPEECH
        tts_layout = QHBoxLayout()
        tts_label = BodyLabel("🔊 TTS Model (Text→Speech):")
        tts_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #e6edf3;")
        tts_layout.addWidget(tts_label)
        self.tts_model_combo = ComboBox()
        self.tts_model_combo.setToolTip("Select text-to-speech model. VibeVoice supports streaming (~300ms latency) and voice cloning")
        tts_models = self.tts_manager.get_available_tts_models()
        for model_id, model_name in tts_models.items():
            self.tts_model_combo.addItem(model_name, userData=model_id)
        # Set current model
        current_tts = self.tts_manager.get_current_tts_model()
        index = self.tts_model_combo.findData(current_tts)
        if index >= 0:
            self.tts_model_combo.setCurrentIndex(index)
        tts_layout.addWidget(self.tts_model_combo)

        # KittenTTS voice selection (initially hidden)
        self.kittentts_voice_combo = ComboBox()
        self.kittentts_voice_combo.addItems(
            ["Bella", "Jasper", "Luna", "Bruno", "Rosie", "Hugo", "Kiki", "Leo"]
        )
        self.kittentts_voice_combo.setCurrentIndex(1)  # Default to Jasper
        self.kittentts_voice_combo.setVisible(False)  # Hidden by default
        tts_layout.addWidget(self.kittentts_voice_combo)

        # VibeVoice voice selection (initially hidden)
        self.vibevoice_voice_combo = ComboBox()
        self.vibevoice_voice_combo.addItems(
            ["Carter", "Emma", "Fable", "Onyx", "Nova", "Shimmer"]
        )
        self.vibevoice_voice_combo.setCurrentIndex(0)  # Default to Carter
        self.vibevoice_voice_combo.setVisible(False)  # Hidden by default
        tts_layout.addWidget(self.vibevoice_voice_combo)

        tts_layout.addStretch()
        content_layout.addLayout(tts_layout)

        # Progress indicator
        self.progress_ring = IndeterminateProgressRing()
        self.progress_ring.setVisible(False)
        content_layout.addWidget(
            self.progress_ring, alignment=Qt.AlignmentFlag.AlignCenter
        )

        # Transcription display
        transcription_card = CardWidget()
        transcription_layout = QVBoxLayout(transcription_card)
        transcription_title = BodyLabel("Your Speech:")
        transcription_title.setStyleSheet(
            "font-weight: bold; font-size: 14px; color: #e6edf3;"
        )
        transcription_layout.addWidget(transcription_title)
        self.transcription_display = TextEdit()
        self.transcription_display.setReadOnly(True)
        self.transcription_display.setMaximumHeight(150)
        self.transcription_display.setStyleSheet("""
            TextEdit {
                background-color: #1a1f26;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 14px;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
                font-size: 15px;
                line-height: 1.6;
                selection-background-color: #238636;
                selection-color: #ffffff;
            }
            TextEdit:hover {
                border-color: #484f58;
            }
            QTextEdit:disabled {
                background-color: #161b22;
                color: #8b949e;
            }
        """)
        transcription_layout.addWidget(self.transcription_display)

        # Custom text toggle + play button
        custom_text_layout = QHBoxLayout()
        custom_text_layout.addWidget(BodyLabel("📝 Custom Text Mode:"))
        self.custom_text_toggle = SwitchButton()
        self.custom_text_toggle.setChecked(False)
        self.custom_text_toggle.checkedChanged.connect(self.on_custom_text_toggled)
        self.custom_text_toggle.setToolTip("Enable to type/paste text, URLs, or search queries. URLs are fetched & read. Searches show results to select.")
        custom_text_layout.addWidget(self.custom_text_toggle)

        self.play_text_btn = PushButton("▶ Play")
        self.play_text_btn.setToolTip("Play the entered text via TTS. Works with plain text, URLs (fetches article), or search queries.")
        self.play_text_btn.clicked.connect(self.on_play_text_clicked)
        self.play_text_btn.setEnabled(False)
        self.play_text_btn.setStyleSheet("""
            PushButton {
                background-color: #238636;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 6px;
            }
            PushButton:hover { background-color: #2ea043; }
            PushButton:disabled { background-color: #30363d; color: #8b949e; }
        """)
        custom_text_layout.addWidget(self.play_text_btn)
        custom_text_layout.addStretch()
        transcription_layout.addLayout(custom_text_layout)

        content_layout.addWidget(transcription_card)

        # Response display
        response_card = CardWidget()
        response_layout = QVBoxLayout(response_card)

        # Response header with title and verbosity selector
        response_header_layout = QHBoxLayout()
        response_title = BodyLabel("AI Response:")
        response_title.setStyleSheet("font-weight: bold;")
        response_header_layout.addWidget(response_title)

        response_header_layout.addStretch()

        # Verbosity selector
        verbosity_label = BodyLabel("Response:")
        verbosity_label.setStyleSheet("font-size: 12px; color: #888888;")
        response_header_layout.addWidget(verbosity_label)

        self.verbosity_combo = ComboBox()
        self.verbosity_combo.addItems(["Concise", "Balanced", "Detailed"])
        self.verbosity_combo.setCurrentIndex(1)  # Default to Balanced
        self.verbosity_combo.setFixedWidth(100)
        response_header_layout.addWidget(self.verbosity_combo)

        translate_label = BodyLabel("Translate:")
        translate_label.setStyleSheet(
            "font-size: 12px; color: #888888; margin-left: 15px;"
        )
        response_header_layout.addWidget(translate_label)

        self.translation_toggle = ToggleButton("", self)
        self.translation_toggle.setFixedWidth(50)
        self.translation_toggle.setChecked(False)
        self.translation_toggle.setToolTip("Enable translation service")
        response_header_layout.addWidget(self.translation_toggle)

        target_lang_label = BodyLabel("Output:")
        target_lang_label.setStyleSheet(
            "font-size: 12px; color: #888888; margin-left: 15px;"
        )
        response_header_layout.addWidget(target_lang_label)

        self.target_language_combo = ComboBox()
        self.target_language_combo.setFixedWidth(120)
        self._populate_target_language_combo()
        self.target_language_combo.currentIndexChanged.connect(
            self.on_target_language_changed
        )
        self.target_language_combo.setEnabled(False)
        response_header_layout.addWidget(self.target_language_combo)

        response_layout.addLayout(response_header_layout)

        # Use Markdown display for response
        self.response_display = ScrollableMarkdownDisplay()
        self.response_display.setMaximumHeight(250)
        response_layout.addWidget(self.response_display)
        content_layout.addWidget(response_card)

        # Mode toggle at the bottom
        mode_layout = QHBoxLayout()
        self.mode_toggle = ToggleButton("Dictation Mode", self)
        self.mode_toggle.setChecked(False)
        mode_layout.addWidget(BodyLabel("Mode:"))
        mode_layout.addWidget(self.mode_toggle)

        # Window selector for dictation mode
        window_label = BodyLabel("Window:")
        window_label.setStyleSheet(
            "font-size: 12px; color: #888888; margin-left: 20px;"
        )
        mode_layout.addWidget(window_label)

        self.window_combo = ComboBox()
        self.window_combo.setFixedWidth(200)
        self.window_combo.setEnabled(False)
        self.window_combo.addItem("Select window...", userData=None)
        mode_layout.addWidget(self.window_combo)

        mode_layout.addStretch()
        content_layout.addLayout(mode_layout)

        content_layout.addStretch()

        # Add content layout to page layout
        page_layout.addLayout(content_layout, 1)

    def connect_signals(self):
        """Connect UI signals to handlers"""
        # Model changes
        self.asr_model_combo.currentIndexChanged.connect(self.on_asr_model_changed)
        self.tts_model_combo.currentIndexChanged.connect(self.on_tts_model_changed)
        self.sensitivity_combo.currentIndexChanged.connect(self.on_sensitivity_changed)

        # Recording controls
        self.trigger_toggle.toggled.connect(self.on_trigger_mode_changed)

        # Translation and verbosity
        self.verbosity_combo.currentTextChanged.connect(self.on_verbosity_changed)
        self.translation_toggle.toggled.connect(self.on_translation_toggled)
        self.target_language_combo.currentIndexChanged.connect(
            self.on_target_language_changed
        )

        # Mode toggle
        self.mode_toggle.toggled.connect(self.on_mode_toggled)

        # TTS model change
        self.tts_model_combo.currentIndexChanged.connect(self.on_tts_model_changed)

        # Window combo
        self.window_combo.currentIndexChanged.connect(self.on_window_changed)

    def _populate_target_language_combo(self):
        """Populate target language combo based on current TTS model"""
        from src.languages import TTS_MODELS

        current_tts = self.tts_manager.get_current_tts_model()
        tts_langs = TTS_MODELS.get(current_tts, {}).get("languages", {"en": "English"})

        self.target_language_combo.blockSignals(True)
        self.target_language_combo.clear()

        # Add "Same as input" option first
        self.target_language_combo.addItem("Same as input", userData="")

        # Add languages supported by current TTS
        for lang_code, lang_name in sorted(tts_langs.items(), key=lambda x: x[1]):
            self.target_language_combo.addItem(lang_name, userData=lang_code)

        # Default to English or first supported language
        default_lang = "en" if "en" in tts_langs else list(tts_langs.keys())[0]
        index = self.target_language_combo.findData(default_lang)
        if index >= 0:
            self.target_language_combo.setCurrentIndex(index)

        self.target_language_combo.blockSignals(False)
        self.current_target_language = (
            self.target_language_combo.currentData() or default_lang
        )

    # === Signal Handlers ===

    def on_asr_model_changed(self, index):
        """Handle ASR model selection change"""
        model_id = self.asr_model_combo.itemData(index)
        if model_id and model_id != self.voice_processor.get_current_asr_model():
            try:
                self.voice_processor.switch_asr_model(model_id)
                InfoBar.success(
                    "ASR Model Changed",
                    f"Switched to {self.asr_model_combo.currentText()}",
                    parent=self,
                    duration=2000,
                )
            except Exception as e:
                InfoBar.error(
                    "ASR Model Error",
                    f"Failed to switch ASR model: {str(e)}",
                    parent=self,
                    duration=3000,
                )

    def on_tts_model_changed(self, index):
        model_id = self.tts_model_combo.itemData(index)

        if model_id and model_id != self.tts_manager.get_current_tts_model():
            try:
                self.tts_manager.switch_tts_model(model_id)
                self._populate_target_language_combo()
            except Exception as e:
                InfoBar.error(
                    "TTS Model Error",
                    f"Failed to switch TTS model: {str(e)}",
                    parent=self,
                    duration=3000,
                )

        is_kittentts = model_id == "kittentts"
        is_vibevoice = model_id == "vibevoice"

        self.kittentts_voice_combo.setVisible(is_kittentts)
        self.vibevoice_voice_combo.setVisible(is_vibevoice)

        if is_kittentts:
            InfoBar.info(
                "KittenTTS Voice",
                f"Voice: {self.kittentts_voice_combo.currentText()}",
                parent=self,
                duration=1500,
            )
        elif is_vibevoice:
            InfoBar.info(
                "VibeVoice Voice",
                f"Voice: {self.vibevoice_voice_combo.currentText()}",
                parent=self,
                duration=1500,
            )
        else:
            InfoBar.success(
                "TTS Model Changed",
                f"Switched to {self.tts_model_combo.currentText()}",
                parent=self,
                duration=2000,
            )

        self.tts_manager.set_current_tts_model(model_id)
        self.settings_manager.set("tts_model", model_id)

    def on_sensitivity_changed(self, index):
        """Handle sensitivity selection change"""
        sensitivity_level = self.sensitivity_combo.currentText()
        if self.waveform_widget:
            self.waveform_widget.set_sensitivity(sensitivity_level)

    def on_trigger_mode_changed(self, checked):
        """Handle trigger mode change"""
        if checked:
            InfoBar.info(
                "Auto VAD Trigger",
                "Audio will be processed automatically when silence is detected",
                parent=self,
                duration=2000,
            )
        else:
            InfoBar.warning(
                "Manual Trigger",
                "Press hotkey or click 'Start Listening' to activate",
                parent=self,
                duration=2000,
            )

    def on_verbosity_changed(self, text):
        """Handle verbosity selection change"""
        verbosity_map = {
            "Concise": "concise",
            "Balanced": "balanced",
            "Detailed": "detailed",
        }
        self.current_verbosity = verbosity_map.get(text, "balanced")
        InfoBar.info(
            "Response Style",
            f"Set to {text}",
            parent=self,
            duration=1500,
        )

    def on_translation_toggled(self, checked):
        """Handle translation toggle"""
        self.translation_enabled = checked
        self.target_language_combo.setEnabled(checked)

        if checked:
            InfoBar.info(
                "Translation",
                "Translation enabled",
                parent=self,
                duration=1500,
            )
        else:
            InfoBar.info(
                "Translation",
                "Translation disabled - direct passthrough",
                parent=self,
                duration=1500,
            )

    def on_target_language_changed(self, index):
        """Handle target language selection change"""
        lang_code = self.target_language_combo.currentData()
        lang_name = self.target_language_combo.currentText()

        if lang_code == "" or lang_code is None:
            self.current_target_language = "en"
            InfoBar.info(
                "Output Language",
                "Will use same as input (no translation)",
                parent=self,
                duration=1500,
            )
        else:
            self.current_target_language = lang_code
            InfoBar.info(
                "Output Language",
                f"Set to {lang_name}",
                parent=self,
                duration=1500,
            )

    def get_kittentts_voice(self):
        """Get selected KittenTTS voice"""
        return self.kittentts_voice_combo.currentText()

    def get_vibevoice_voice(self):
        """Get selected VibeVoice voice"""
        return self.vibevoice_voice_combo.currentText()

    def on_mode_toggled(self, checked):
        """Handle mode toggle between Voice AI and Dictation"""
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

    def on_window_changed(self, index):
        """Handle window selection change"""
        window_id = self.window_combo.currentData()
        if window_id:
            InfoBar.info(
                "Window Selected",
                f"Dictation will be injected to window ID: {window_id}",
                parent=self,
                duration=1500,
            )

    def _toggle_mini_mode(self):
        """Toggle mini mode via main window"""
        self.main_window.toggle_mini_mode()

    # === Public Methods for MainWindow ===

    def manual_activate(self):
        """Manually activate listening"""
        if not self.trigger_toggle.isChecked():
            self.start_listening_requested.emit()

    def start_listening(self):
        """Start enhanced recording with multi-threading support"""
        self.listen_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        # Update UI state
        self.recording_status_label.setText("Listening...")
        self.recording_status_label.setStyleSheet("color: #4A90E2; font-size: 12px;")

        # Start recording timer
        self.recording_start_time = time.time()

        # Start enhanced recording
        success = self.voice_processor.start_recording()
        if success:
            InfoBar.info(
                "Listening Started",
                "Speak your query/dictation - unlimited duration supported",
                parent=self,
                duration=2000,
            )
        else:
            InfoBar.error(
                "Listening Error",
                "Failed to start listening",
                parent=self,
                duration=3000,
            )
            self.stop_listening()  # Reset UI state

    def stop_listening(self):
        """Stop listening and process the audio"""
        # Stop recording timer
        self.recording_start_time = 0

        # Update UI state to processing
        self.recording_status_label.setText("Processing...")
        self.recording_status_label.setStyleSheet("color: #FF6B6B; font-size: 12px;")
        self.recording_timer_label.setText("Processing")

        # Stop recording and get combined audio
        audio_data = self.voice_processor.stop_recording()

        if audio_data is not None and len(audio_data) > 0:
            # Process the audio
            self.main_window.process_audio(audio_data)

            # Log recording statistics
            recording_info = self.voice_processor.get_recording_state()
            print(
                f"Processed {len(audio_data) / 16000:.1f}s of audio from {recording_info['segment_count']} segments"
            )
        else:
            InfoBar.warning(
                "No Audio",
                "No audio was recorded",
                parent=self,
                duration=2000,
            )
            self.on_processing_finished()  # Reset UI state

    def update_transcription(self, text):
        """Update transcription display and save to session"""
        # Append new text instead of replacing
        current_text = self.transcription_display.toPlainText()
        if current_text and not current_text.endswith("\n"):
            self.transcription_display.append("")
        self.transcription_display.append(text)

        # Auto-scroll to bottom
        self.transcription_display.verticalScrollBar().setValue(
            self.transcription_display.verticalScrollBar().maximum()
        )

        # Save to chat session
        if text.strip():
            session = self.chat_session_manager.get_current_session()
            if session:
                session.add_message("user", text)

    def update_response(self, text):
        """Update response display with markdown"""
        # Append new text instead of replacing
        current_text = self.response_display.toPlainText()
        if current_text and not current_text.endswith("\n"):
            self.response_display.append("")
        self.response_display.append(text)

        # Auto-scroll to bottom
        self.response_display.verticalScrollBar().setValue(
            self.response_display.verticalScrollBar().maximum()
        )

        # Save to chat session
        session = self.chat_session_manager.get_current_session()
        if session:
            session.add_message("assistant", text)

    def update_recording_timer(self):
        """Update the recording timer display"""
        if self.recording_start_time > 0:
            elapsed_time = time.time() - self.recording_start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            self.recording_timer_label.setText(time_str)

    def on_processing_started(self):
        """Handle processing started event"""
        self.progress_ring.setVisible(True)
        self.listen_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def on_processing_finished(self):
        """Handle processing finished event"""
        self.progress_ring.setVisible(False)
        self.listen_button.setEnabled(True)
        if not self.trigger_toggle.isChecked():
            self.stop_button.setEnabled(False)

    def on_custom_text_toggled(self, checked):
        """Toggle between transcription mode and custom text input mode"""
        self.transcription_display.setReadOnly(not checked)
        if checked:
            self.transcription_display.setPlaceholderText(
                "Enter custom text here and click Play..."
            )
            self.play_text_btn.setVisible(True)
            self.play_text_btn.setEnabled(True)  # Enable the button
            # Clear and focus for input
            self.transcription_display.clear()
            self.transcription_display.setFocus()
        else:
            self.transcription_display.setPlaceholderText("")
            self.play_text_btn.setVisible(False)
            self.play_text_btn.setEnabled(False)  # Disable when hidden

    def on_play_text_clicked(self):
        """Play the custom text input using TTS - handles URLs, search queries, and plain text"""
        text = self.transcription_display.toPlainText().strip()
        if not text:
            return

        # Detect if input is a URL
        url_pattern = re.compile(
            r"^(https?://)?"  # Optional protocol
            r"(?:[-\w.]|(?:%[\da-fA-F]{2}))+"  # Domain
            r"(?::\d+)?"  # Optional port
            r"(?:/|$|#|\?)",  # Path or end
            re.IGNORECASE,
        )

        is_url = bool(url_pattern.match(text)) or text.startswith(
            ("http://", "https://")
        )

        # If it looks like a URL but doesn't have protocol, add https://
        if is_url and not text.startswith(("http://", "https://")):
            text = f"https://{text}"
            is_url = True

        if is_url:
            # Process URL through URLProcessor
            self._process_url_and_speak(text)
            return

        # Check if it looks like a search query (contains question or search keywords)
        search_keywords = ['what', 'how', 'why', 'when', 'where', 'who', 'explain', 'search', 'find', 'latest', 'news', '?', 'tell me']
        is_search = any(text.lower().startswith(kw) or f" {kw}" in text.lower() for kw in search_keywords)
        
        if is_search:
            # Run web search and show results
            self._run_web_search(text)
            return

        # Plain text - just speak it
        self._speak_text(text)

    def get_dictation_mode(self):
        """Get current dictation mode state"""
        return self.mode_toggle.isChecked()

    def get_verbosity(self):
        """Get current verbosity level"""
        return self.current_verbosity

    def get_translation_enabled(self):
        """Get translation enabled state"""
        return self.translation_enabled

    def get_target_language(self):
        """Get target language code"""
        return self.current_target_language

    def get_dictation_window_id(self):
        """Get selected window ID for dictation"""
        if self.mode_toggle.isChecked():
            return self.window_combo.currentData()
        return None

    # === Private Methods ===

    def _on_session_selected(self, session_id: str):
        """Handle session selection from sidebar"""
        self.chat_session_manager.switch_session(session_id)
        session = self.chat_session_manager.get_current_session()

        if session and session.messages:
            # Load conversation history for this session
            if hasattr(self.main_window, "voice_worker"):
                self.main_window.voice_worker.conversation_history = [
                    msg
                    for msg in session.messages
                    if msg.get("role") in ["user", "assistant"]
                ]

            # Display last assistant response if exists
            for msg in reversed(session.messages):
                if msg.get("role") == "assistant":
                    self.response_display.setMarkdown(msg.get("content", ""))
                    break
        else:
            self.response_display.clear()
            self.transcription_display.clear()
            if hasattr(self.main_window, "voice_worker"):
                self.main_window.voice_worker.conversation_history = []

        self.chat_sidebar.refresh_session_list()

    def _on_new_chat(self):
        """Handle new chat request"""
        # Clear current displays
        self.response_display.clear()
        self.transcription_display.clear()
        if hasattr(self.main_window, "voice_worker"):
            self.main_window.voice_worker.conversation_history = []

        # Create new session
        self.chat_session_manager.create_new_session()
        self.chat_sidebar.refresh_session_list()


    def _is_search_query(self, text: str) -> bool:
        """Check if text is a search query (not URL, not command)"""
        text = text.strip()
        
        # Not a URL
        url_pattern = r'^https?://|^www\.|^[a-zA-Z0-9]+\.[a-zA-Z]'
        if re.match(url_pattern, text, re.IGNORECASE):
            return False
        
        # Not a command (starts with /)
        if text.startswith('/'):
            return False
        
        # Looks like a search query
        # - Contains question marks, or
        # - Has multiple words and no punctuation like URLs
        search_indicators = ['?', 'how', 'what', 'why', 'when', 'where', 'who', 'which', 'latest', 'news', 'search']
        is_search = any(indicator in text.lower() for indicator in search_indicators)
        
        # Also treat plain multi-word text as search if it doesn't look like a sentence
        if not is_search and len(text.split()) >= 2:
            # Check if it has URL-like patterns
            if '.' not in text and '/' not in text:
                is_search = True
        
        return is_search

    def _run_web_search(self, query: str, max_results: int = 5):
        """Run web search and return results"""
        from src.web_search import TavilySearch
        import os
        
        api_key = os.environ.get("TAVILY_API_KEY", "")
        if not api_key:
            # Try settings manager
            api_key = self.settings_manager.get("tavily_api_key", "")
        
        if not api_key:
            logger.warning("No Tavily API key found")
            return []
        
        try:
            search = TavilySearch(api_key=api_key)
            results = search.search(query, max_results=max_results)
            return results.get("results", [])
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def _process_url_and_speak(self, url: str, title: str = None):
        """Process URL through archive.is and speak"""
        from src.url_processor import URLProcessor
        
        def progress_callback(msg):
            self._append_status(msg)
        
        try:
            processor = URLProcessor()
            result = processor.process(url, progress_callback=progress_callback)
            
            content = result.get("content", "")
            article_title = result.get("title", title or "Article")
            
            if content:
                # Display in transcription box
                self.transcription_display.append(f"📰 {article_title}\n{content[:500]}...")
                
                # Speak the content
                self._speak_text(content)
            else:
                self._append_status("⚠️ No content extracted")
                
        except Exception as e:
            logger.error(f"URL processing failed: {e}")
            self._append_status(f"❌ Failed: {e}")

    def _append_status(self, msg: str):
        """Append a status message to the transcription display"""
        if hasattr(self, 'transcription_display') and self.transcription_display:
            self.transcription_display.append(msg)

    def _speak_text(self, text: str):
        """Synthesize and play text via TTS"""
        if not text:
            return
        
        # Get TTS settings
        tts_model = self.settings_manager.get("tts_model", "kittentts")
        streaming = self.settings_manager.get("tts_streaming", False)
        
        # Get voice/language for VibeVoice
        voice = None
        language = None
        if tts_model == "vibevoice":
            voice = self.settings_manager.get("vibevoice_voice", "Carter")
            language = self.settings_manager.get("vibevoice_language", "en")
        
        try:
            # Use voice_worker to synthesize
            if hasattr(self.main_window, "voice_worker"):
                self.main_window.voice_worker.synthesize_and_play(
                    text,
                    model=tts_model,
                    voice=voice,
                    language=language,
                    streaming=streaming
                )
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            self._append_status(f"❌ TTS failed: {e}")

    def _show_search_results_dialog(self, query: str, results: list):
        """Show search results in a dialog for user to select"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QLabel, QPushButton, QHBoxLayout
        from PySide6.QtCore import Qt
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Search Results: {query}")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Header
        header = QLabel(f"Select an article to read ({len(results)} results):")
        layout.addWidget(header)
        
        # Results list
        list_widget = QListWidget()
        for i, result in enumerate(results):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            content = result.get("content", "")[:100] + "..."
            
            item_text = f"{i+1}. {title}\n   {url}\n   {content}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, result)
            list_widget.addItem(item)
        
        layout.addWidget(list_widget)
        
        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        
        def on_select():
            selected = list_widget.currentItem()
            if selected:
                result = selected.data(Qt.UserRole)
                url = result.get("url", "")
                title = result.get("title", "")
                dialog.accept()
                # Process selected URL
                self._process_url_and_speak(url, title)
        
        select_btn = QPushButton("Read Selected")
        select_btn.clicked.connect(on_select)
        btn_layout.addWidget(select_btn)
        
        layout.addLayout(btn_layout)
        
        # Double-click to select
        list_widget.itemDoubleClicked.connect(on_select)
        
        dialog.exec()

