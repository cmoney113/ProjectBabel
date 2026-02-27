#!/usr/bin/env python3
"""
Canary Voice AI Assistant - Modern PySide6/Fluent UI Application

Features:
- Canary-1b-v2 ASR -> Groq openai/gpt-oss-120b -> NeuTTS-Nano pipeline
- Two modes: Voice AI Assistant and Dictation Mode
- Toggle between VAD auto-trigger and manual key press
- Dark navy theme with Fluent UI animations and transitions
- Real-time speech transcription and model response display
- Tavily web search integration for current events and comprehensive answers
- Context-aware conversation history
- Configurable hotkey for manual activation
"""

import sys
import os
import json
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Qt and Fluent widgets
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread, Slot
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
)
from PySide6.QtGui import QFont, QColor, QKeySequence, QShortcut
from qfluentwidgets import (
    setTheme,
    Theme,
    FluentIcon,
    NavigationInterface,
    NavigationItemPosition,
    FluentWindow,
    SubtitleLabel,
    BodyLabel,
    PushButton,
    ToggleButton,
    ComboBox,
    SpinBox,
    LineEdit,
    TextEdit,
    CardWidget,
    InfoBar,
    InfoBarPosition,
    SmoothScrollArea,
    ToolTipFilter,
    setFont,
    Flyout,
    FlyoutViewBase,
    PrimaryPushButton,
    TransparentToolButton,
    IndeterminateProgressRing,
    PillPushButton,
    StateToolTip,
    TeachingTip,
    TeachingTipTailPosition,
)

# Import our modules
from src.voice_processor import VoiceProcessor
from src.enhanced_voice_processor import EnhancedVoiceProcessor
from src.llm_manager import LLMManager
from src.tts_manager import TTSManager
from src.web_search import WebSearchManager
from src.settings_manager import SettingsManager
from src.circular_waveform import CircularWaveformWidget
from src.chat_session_manager import ChatSessionManager
from src.chat_sidebar import ChatSidebar
from src.markdown_display import MarkdownDisplay, ScrollableMarkdownDisplay
from src.languages import CANARY_LANGUAGES, TTS_MODELS, get_tts_languages


class WorkerSignals(QObject):
    """Signals for worker threads"""

    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class VoiceAIWorker(QThread):
    """Background worker for voice processing"""

    transcription_ready = Signal(str)
    response_ready = Signal(str)
    processing_started = Signal()
    processing_finished = Signal()
    error_occurred = Signal(str)

    def __init__(
        self,
        voice_processor,
        llm_manager,
        tts_manager,
        web_search_manager,
        settings_manager=None,
    ):
        super().__init__()
        self.voice_processor = voice_processor
        self.llm_manager = llm_manager
        self.tts_manager = tts_manager
        self.web_search_manager = web_search_manager
        self.settings_manager = settings_manager
        self.current_audio = None
        self.is_dictation_mode = False
        self.conversation_history = []
        self.translation_enabled = False

        # Import new pipeline components
        from src.pipeline import get_voice_pipeline

        self.pipeline = (
            get_voice_pipeline(settings_manager) if settings_manager else None
        )
        self.current_verbosity = "balanced"
        self.target_language = "en"
        self.current_tts_model = "chatterbox-fp16"

    def set_audio(self, audio_data):
        self.current_audio = audio_data

    def set_dictation_mode(self, enabled: bool):
        self.is_dictation_mode = enabled

    def set_verbosity(self, verbosity: str):
        self.current_verbosity = verbosity

    def set_target_language(self, lang: str):
        self.target_language = lang
    def run(self):
        if self.current_audio is None:
            return

        try:
            self.processing_started.emit()

            # Transcribe audio with language detection
            transcription_result = self.voice_processor.transcribe_with_language(self.current_audio)
            transcription = transcription_result.text
            detected_language = transcription_result.detected_language
            
            self.transcription_ready.emit(transcription)

            # Log language detection info
            self.logger.info(f"Detected language: {detected_language} (confidence: {transcription_result.confidence})")

            if self.is_dictation_mode:
                # Dictation mode: translate if needed, then clean up via Wbind
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if self.pipeline:
                    result = loop.run_until_complete(
                        self.pipeline.process_dictation(
                            audio_data=transcription,
                            detected_language=detected_language,
                            target_language=self.target_language,
                        )
                    )
                    processed_text = result.output_text
                else:
                    # Fallback to old method
                    processed_text = self.llm_manager.process_dictation(transcription)

                self.response_ready.emit(processed_text)
                # Output to wbind for typing
                self.tts_manager.type_text(processed_text)
            else:
                # Voice AI mode: translate if needed, then process via iFlow
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if self.pipeline:
                    result = loop.run_until_complete(
                        self.pipeline.process_voice_ai(
                            audio_data=transcription,
                            detected_language=detected_language,
                            target_language=self.target_language,
                            tts_model=self.current_tts_model,
                            verbosity=self.current_verbosity,
                        )
                    )
                    response = result.output_text
                else:
                    # Fallback to old method
                    should_search = self.web_search_manager.should_perform_search(
                        transcription, confidence_threshold=0.85
                    )
                    if should_search:
                        search_results = self.web_search_manager.search(transcription)
                        response = self.llm_manager.generate_response_with_context(
                            transcription, self.conversation_history, search_results
                        )
                    else:
                        response = self.llm_manager.generate_response_with_context(
                            transcription, self.conversation_history
                        )

                self.response_ready.emit(response)
                self.conversation_history.append({"role": "user", "content": transcription})
                self.conversation_history.append({"role": "assistant", "content": response})
                
                # Speak response via TTS
                self.tts_manager.speak(response)

            self.processing_finished.emit()

        except Exception as e:
            self.error_occurred.emit(str(e))
            self.processing_finished.emit()
                self.conversation_history.append({"role": "user", "content": transcription})
                self.conversation_history.append({"role": "assistant", "content": response})
                
                # Speak response via TTS
                self.tts_manager.speak(response)

            self.processing_finished.emit()

        except Exception as e:
            self.error_occurred.emit(str(e))
            self.processing_finished.emit()


class MainWindow(FluentWindow):
    """Main application window with Fluent UI"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Canary Voice AI Assistant")
        self.resize(1200, 800)

        # Initialize managers
        self.settings_manager = SettingsManager()
        # Use enhanced voice processor for multi-threading support
        self.voice_processor = EnhancedVoiceProcessor(self.settings_manager)
        self.llm_manager = LLMManager(self.settings_manager)
        self.tts_manager = TTSManager(self.settings_manager)
        self.web_search_manager = WebSearchManager(self.settings_manager)

        # Chat session manager
        self.chat_session_manager = ChatSessionManager()
        self.current_verbosity = "balanced"
        self.current_target_language = "en"
        self.translation_enabled = False

        # Initialize timers
        self.recording_timer = QTimer(self)
        self.recording_timer.timeout.connect(self.update_recording_timer)
        self.recording_start_time = 0

        # Initialize logger
        import logging

        self.logger = logging.getLogger(__name__)

        # Initialize logger
        import logging

        self.logger = logging.getLogger(__name__)

        # Initialize UI
        self.init_ui()
        self.init_workers()
        self.init_shortcuts()

        # Set dark navy theme
        setTheme(Theme.DARK)
        self.setStyleSheet("""
            QMainWindow, FluentWindow {
                background-color: #0a0f1d;
            }
        """)

        # Show welcome teaching tip
        self.show_welcome_tip()

    def init_ui(self):
        """Initialize the user interface"""
        # Create main page
        self.main_page = self.create_main_page()

        # Create status widget (just for spacing, no labels)
        # Create main page
        self.main_page = self.create_main_page()

        # Add navigation items
        self.addSubInterface(self.main_page, FluentIcon.HOME, "Voice AI")

        # Create additional tabs
        self.voice_cloning_page = self.create_voice_cloning_page()
        self.addSubInterface(
            self.voice_cloning_page, FluentIcon.MICROPHONE, "Voice Cloning"
        )

        self.settings_page = self.create_settings_page()
        self.addSubInterface(self.settings_page, FluentIcon.SETTING, "Settings")

    def create_main_page(self):
        """Create the main page with all controls and displays"""
        page = QWidget()
        page.setObjectName("voice_ai_page")  # Set object name for FluentWindow

        # Main horizontal layout: sidebar + content
        page_layout = QHBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # Create sidebar
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
        header_layout.addStretch()
        content_layout.addLayout(header_layout)

        # Recording controls and waveform
        recording_layout = QHBoxLayout()

        # Control buttons
        button_layout = QVBoxLayout()
        self.listen_button = PrimaryPushButton("Start Listening")
        self.listen_button.clicked.connect(self.start_listening)
        self.stop_button = PushButton("Stop Listening")
        self.stop_button.clicked.connect(self.stop_listening)
        self.stop_button.setEnabled(False)
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
        self.sensitivity_combo.currentIndexChanged.connect(self.on_sensitivity_changed)
        sensitivity_layout.addWidget(self.sensitivity_combo)

        sensitivity_layout.addSpacing(20)

        # Auto VAD toggle
        self.trigger_toggle = ToggleButton("Auto VAD")
        self.trigger_toggle.setChecked(False)
        self.trigger_toggle.toggled.connect(self.toggle_trigger_mode)
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

        # ASR Model selection
        asr_layout = QHBoxLayout()
        asr_layout.addWidget(BodyLabel("ASR Model:"))
        self.asr_model_combo = ComboBox()
        asr_models = self.voice_processor.get_available_asr_models()
        for model_id, model_name in asr_models.items():
            self.asr_model_combo.addItem(model_name, userData=model_id)
        # Set current model
        current_asr = self.voice_processor.get_current_asr_model()
        index = self.asr_model_combo.findData(current_asr)
        if index >= 0:
            self.asr_model_combo.setCurrentIndex(index)
        self.asr_model_combo.currentIndexChanged.connect(self.on_asr_model_changed)
        asr_layout.addWidget(self.asr_model_combo)
        asr_layout.addStretch()
        content_layout.addLayout(asr_layout)

        # TTS Model selection
        tts_layout = QHBoxLayout()
        tts_layout.addWidget(BodyLabel("TTS Model:"))
        self.tts_model_combo = ComboBox()
        tts_models = self.tts_manager.get_available_tts_models()
        for model_id, model_name in tts_models.items():
            self.tts_model_combo.addItem(model_name, userData=model_id)
        # Set current model
        current_tts = self.tts_manager.get_current_tts_model()
        index = self.tts_model_combo.findData(current_tts)
        if index >= 0:
            self.tts_model_combo.setCurrentIndex(index)
        self.tts_model_combo.currentIndexChanged.connect(self.on_tts_model_changed)
        tts_layout.addWidget(self.tts_model_combo)
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
        transcription_title.setStyleSheet("font-weight: bold;")
        transcription_layout.addWidget(transcription_title)
        self.transcription_display = TextEdit()
        self.transcription_display.setReadOnly(True)
        self.transcription_display.setMaximumHeight(150)
        content_layout.addWidget(self.transcription_display)
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
        self.verbosity_combo.currentTextChanged.connect(self._on_verbosity_changed)
        response_header_layout.addWidget(self.verbosity_combo)

        translate_label = BodyLabel("Translate:")
        translate_label.setStyleSheet("font-size: 12px; color: #888888; margin-left: 15px;")
        response_header_layout.addWidget(translate_label)

        self.translation_toggle = ToggleButton("", self)
        self.translation_toggle.setFixedWidth(50)
        self.translation_toggle.setChecked(False)
        self.translation_toggle.setToolTip("Enable translation service")
        self.translation_toggle.toggled.connect(self._on_translation_toggled)
        response_header_layout.addWidget(self.translation_toggle)

        target_lang_label = BodyLabel("Output:")
        target_lang_label.setStyleSheet("font-size: 12px; color: #888888; margin-left: 15px;")
        response_header_layout.addWidget(target_lang_label)

        self.target_language_combo = ComboBox()
        self.target_language_combo.setFixedWidth(120)
        self._populate_target_language_combo()
        self.target_language_combo.currentIndexChanged.connect(
            self._on_target_language_changed
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
        self.mode_toggle.toggled.connect(self.toggle_mode)
        mode_layout.addWidget(BodyLabel("Mode:"))
        mode_layout.addWidget(self.mode_toggle)
        mode_layout.addStretch()
        content_layout.addLayout(mode_layout)

        content_layout.addStretch()

        # Add content layout to page layout
        page_layout.addLayout(content_layout, 1)

        return page

    def create_voice_cloning_page(self):
        """Create the voice cloning page"""
        page = QWidget()
        page.setObjectName("voice_cloning_page")
        layout = QVBoxLayout(page)

        # Header
        header_layout = QHBoxLayout()
        title = SubtitleLabel("Voice Cloning")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # TTS Model selection for voice cloning
        tts_clone_layout = QHBoxLayout()
        tts_clone_layout.addWidget(BodyLabel("TTS Model for Cloning:"))
        self.clone_tts_combo = ComboBox()
        tts_models = self.tts_manager.get_available_tts_models()
        for model_id, model_name in tts_models.items():
            # Only add models that support voice cloning (Chatterbox FP16)
            if model_id == "chatterbox-fp16":
                self.clone_tts_combo.addItem(model_name, userData=model_id)
        # Set current model
        current_tts = self.tts_manager.get_current_tts_model()
        if current_tts == "chatterbox-fp16":
            index = self.clone_tts_combo.findData(current_tts)
            if index >= 0:
                self.clone_tts_combo.setCurrentIndex(index)
        self.clone_tts_combo.currentIndexChanged.connect(
            self.on_clone_tts_model_changed
        )
        tts_clone_layout.addWidget(self.clone_tts_combo)
        tts_clone_layout.addStretch()
        layout.addLayout(tts_clone_layout)

        # Reference audio selection
        ref_audio_layout = QHBoxLayout()
        ref_audio_layout.addWidget(BodyLabel("Reference Audio:"))
        self.ref_audio_path_edit = LineEdit()
        self.ref_audio_path_edit.setPlaceholderText("Path to reference audio file...")
        self.ref_audio_path_edit.setText(
            self.settings_manager.get("voice_cloning", {}).get(
                "reference_audio_path", ""
            )
        )
        ref_audio_layout.addWidget(self.ref_audio_path_edit)
        self.browse_ref_audio_btn = PushButton("Browse")
        self.browse_ref_audio_btn.clicked.connect(self.browse_reference_audio)
        ref_audio_layout.addWidget(self.browse_ref_audio_btn)
        ref_audio_layout.addStretch()
        layout.addLayout(ref_audio_layout)

        # Voice cloning text input
        clone_text_layout = QVBoxLayout()
        clone_text_layout.addWidget(BodyLabel("Text to Clone:"))
        self.clone_text_edit = TextEdit()
        self.clone_text_edit.setPlaceholderText(
            "Enter text to synthesize with cloned voice..."
        )
        self.clone_text_edit.setMaximumHeight(150)
        clone_text_layout.addWidget(self.clone_text_edit)
        layout.addLayout(clone_text_layout)

        # Voice cloning controls
        clone_controls_layout = QHBoxLayout()
        self.clone_generate_btn = PrimaryPushButton("Generate Cloned Voice")
        self.clone_generate_btn.clicked.connect(self.generate_cloned_voice)
        self.clone_play_btn = PushButton("Play")
        self.clone_play_btn.clicked.connect(self.play_cloned_voice)
        self.clone_play_btn.setEnabled(False)
        self.clone_save_btn = PushButton("Save Audio")
        self.clone_save_btn.clicked.connect(self.save_cloned_voice)
        self.clone_save_btn.setEnabled(False)
        clone_controls_layout.addWidget(self.clone_generate_btn)
        clone_controls_layout.addWidget(self.clone_play_btn)
        clone_controls_layout.addWidget(self.clone_save_btn)
        clone_controls_layout.addStretch()
        layout.addLayout(clone_controls_layout)

        # Progress indicator for voice cloning
        self.clone_progress_ring = IndeterminateProgressRing()
        self.clone_progress_ring.setVisible(False)
        layout.addWidget(
            self.clone_progress_ring, alignment=Qt.AlignmentFlag.AlignCenter
        )

        # Cloned voice preview
        clone_preview_card = CardWidget()
        clone_preview_layout = QVBoxLayout(clone_preview_card)
        clone_preview_title = BodyLabel("Generated Audio Preview:")
        clone_preview_title.setStyleSheet("font-weight: bold;")
        clone_preview_layout.addWidget(clone_preview_title)
        self.clone_audio_info = BodyLabel("No audio generated yet")
        self.clone_audio_info.setStyleSheet("color: #666666;")
        clone_preview_layout.addWidget(self.clone_audio_info)
        layout.addWidget(clone_preview_card)

        # Voice cloning settings
        clone_settings_card = CardWidget()
        clone_settings_layout = QVBoxLayout(clone_settings_card)
        clone_settings_title = BodyLabel("Voice Cloning Settings:")
        clone_settings_title.setStyleSheet("font-weight: bold;")
        clone_settings_layout.addWidget(clone_settings_title)

        # Language selection for multilingual models
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(BodyLabel("Language:"))
        self.clone_language_combo = ComboBox()
        supported_langs = {
            "en": "English",
            "fr": "French",
            "de": "German",
            "es": "Spanish",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic",
        }
        for lang_code, lang_name in supported_langs.items():
            self.clone_language_combo.addItem(lang_name, userData=lang_code)
        self.clone_language_combo.setCurrentIndex(0)  # Default to English
        lang_layout.addWidget(self.clone_language_combo)
        lang_layout.addStretch()
        clone_settings_layout.addLayout(lang_layout)

        # Advanced settings
        advanced_layout = QHBoxLayout()
        self.exaggeration_spin = SpinBox()
        self.exaggeration_spin.setRange(0, 100)
        self.exaggeration_spin.setValue(30)  # 0.3 default
        self.exaggeration_spin.setSuffix("%")
        advanced_layout.addWidget(BodyLabel("Emotion Exaggeration:"))
        advanced_layout.addWidget(self.exaggeration_spin)
        advanced_layout.addSpacing(20)

        self.temperature_spin = SpinBox()
        self.temperature_spin.setRange(0, 100)
        self.temperature_spin.setValue(80)  # 0.8 default
        self.temperature_spin.setSuffix("%")
        advanced_layout.addWidget(BodyLabel("Temperature:"))
        advanced_layout.addWidget(self.temperature_spin)
        advanced_layout.addStretch()
        clone_settings_layout.addLayout(advanced_layout)
        layout.addWidget(clone_settings_card)

        layout.addStretch()

        # Initialize voice cloning state
        self.cloned_audio_data = None
        self.cloned_audio_sample_rate = 24000

        return page

    def init_workers(self):
        """Initialize background workers"""
        self.voice_worker = VoiceAIWorker(
            self.voice_processor,
            self.llm_manager,
            self.tts_manager,
            self.web_search_manager,
            self.settings_manager,
        )
        self.voice_worker.transcription_ready.connect(self.update_transcription)
        self.voice_worker.response_ready.connect(self.update_response)
        self.voice_worker.processing_started.connect(self.on_processing_started)
        self.voice_worker.processing_finished.connect(self.on_processing_finished)
        self.voice_worker.error_occurred.connect(self.on_error)

    def init_shortcuts(self):
        """Initialize keyboard shortcuts"""
        self.hotkey_shortcut = QShortcut(QKeySequence("Ctrl+Space"), self)
        self.hotkey_shortcut.activated.connect(self.manual_activate)

    def toggle_mode(self, checked):
        """Toggle between Voice AI and Dictation modes"""
        if checked:
            InfoBar.success(
                "Dictation Mode",
                "Using post-processing prompt for clean transcription output",
                parent=self,
                duration=2000,
            )
        else:
            InfoBar.info(
                "Voice AI Mode",
                "Using conversational AI with context awareness",
                parent=self,
                duration=2000,
            )

    def toggle_trigger_mode(self, checked):
        """Toggle between VAD auto-trigger and manual trigger"""
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
        """Handle TTS model selection change"""
        model_id = self.tts_model_combo.itemData(index)
        if model_id and model_id != self.tts_manager.get_current_tts_model():
            try:
                self.tts_manager.switch_tts_model(model_id)
                self._populate_target_language_combo()
                InfoBar.success(
                    "TTS Model Changed",
                    f"Switched to {self.tts_model_combo.currentText()}",
                    parent=self,
                    duration=2000,
                )
            except Exception as e:
                InfoBar.error(
                    "TTS Model Error",
                    f"Failed to switch TTS model: {str(e)}",
                    parent=self,
                    duration=3000,
                )

    def on_sensitivity_changed(self, index):
        """Handle sensitivity selection change"""
        sensitivity_level = self.sensitivity_combo.currentText()
        if hasattr(self, "waveform_widget") and self.waveform_widget:
            self.waveform_widget.set_sensitivity(sensitivity_level)

        # Optionally also update the voice processor sensitivity if it has that capability
        if hasattr(self, "voice_processor"):
            # Update voice processor sensitivity if it has this method
            pass

    def update_recording_timer(self):
        """Update the recording timer display"""
        import time

        elapsed_time = time.time() - self.recording_start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        time_str = f"{minutes:02d}:{seconds:02d}"
        self.recording_timer_label.setText(time_str)

    def manual_activate(self):
        """Manually activate listening"""
        if not self.trigger_toggle.isChecked():
            self.start_listening()

    def start_listening(self):
        """Start enhanced recording with multi-threading support"""
        self.listen_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        # Update UI state
        self.recording_status_label.setText("Listening...")
        self.recording_status_label.setStyleSheet("color: #4A90E2; font-size: 12px;")

        # Start recording timer
        self.recording_start_time = time.time()
        self.recording_timer.start(100)  # Update every 100ms

        # Start enhanced recording and listening
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
        self.recording_timer.stop()

        # Update UI state to processing
        self.recording_status_label.setText("Processing...")
        self.recording_status_label.setStyleSheet("color: #FF6B6B; font-size: 12px;")
        self.recording_timer_label.setText("Processing")

        # Stop recording and get combined audio
        audio_data = self.voice_processor.stop_recording()

        if audio_data is not None and len(audio_data) > 0:
            # Process the audio
            self.process_audio(audio_data)

            # Log recording statistics
            recording_info = self.voice_processor.get_recording_state()
            self.logger.info(
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

    def process_audio(self, audio_data):
        """Process audio data in background thread"""
        self.voice_worker.set_audio(audio_data)
        self.voice_worker.set_dictation_mode(self.mode_toggle.isChecked())
        self.voice_worker.set_verbosity(self.current_verbosity)

        # Get target language from dropdown and translation enabled
        target_lang = self.current_target_language if self.translation_enabled else ""
        self.voice_worker.set_target_language(target_lang)
        self.voice_worker.set_translation_enabled(self.translation_enabled)

        # Get current TTS model
        current_tts = self.tts_manager.get_current_tts_model()
        self.voice_worker.set_tts_model(current_tts)

        self.voice_worker.start()

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

    def on_error(self, error_message):
        """Handle error events"""
        InfoBar.error("Error", error_message, parent=self, duration=5000)
        self.progress_ring.setVisible(False)
        self.listen_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def update_transcription(self, text):
        """Update transcription display and save to session"""
        self.transcription_display.setText(text)

        # Save to chat session
        if text.strip():
            session = self.chat_session_manager.get_current_session()
            if session:
                session.add_message("user", text)

    def update_response(self, text):
        """Update response display with markdown"""
        self.response_display.setMarkdown(text)

        # Save to chat session
        session = self.chat_session_manager.get_current_session()
        if session:
            session.add_message("assistant", text)

    # Chat sidebar signal handlers
    def _on_session_selected(self, session_id: str):
        """Handle session selection from sidebar"""
        self.chat_session_manager.switch_session(session_id)
        session = self.chat_session_manager.get_current_session()

        if session and session.messages:
            # Load conversation history for this session
            self.voice_worker.conversation_history = [
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
            self.voice_worker.conversation_history = []

        self.chat_sidebar.refresh_session_list()

    def _on_new_chat(self):
        """Handle new chat request"""
        # Clear current displays
        self.response_display.clear()
        self.transcription_display.clear()
        self.voice_worker.conversation_history = []

        # Create new session
        self.chat_session_manager.create_new_session()
        self.chat_sidebar.refresh_session_list()

    def _on_verbosity_changed(self, text):
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

    def _on_target_language_changed(self, index):
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


    def _on_translation_toggled(self, checked):
        """Handle translation toggle - master control for translation"""
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

    def create_settings_page(self):
        """Create comprehensive settings page"""
        page = QWidget()
        page.setObjectName("settings_page")
        layout = QVBoxLayout(page)

        # Header
        header_layout = QHBoxLayout()
        title = SubtitleLabel("Settings")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Scroll area for settings
        scroll_area = SmoothScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # ASR Settings Section
        asr_settings_card = CardWidget()
        asr_settings_layout = QVBoxLayout(asr_settings_card)
        asr_title = SubtitleLabel("ASR Model Settings")
        asr_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        asr_settings_layout.addWidget(asr_title)

        # Canary 1B v2 Settings
        canary_group = self._create_canary_settings()
        asr_settings_layout.addWidget(canary_group)

        # Parakeet TDT v3 Settings
        parakeet_group = self._create_parakeet_settings()
        asr_settings_layout.addWidget(parakeet_group)

        scroll_layout.addWidget(asr_settings_card)

        # TTS Settings Section
        tts_settings_card = CardWidget()
        tts_settings_layout = QVBoxLayout(tts_settings_card)
        tts_title = SubtitleLabel("TTS Model Settings")
        tts_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        tts_settings_layout.addWidget(tts_title)

        # NeuTTS-Nano Settings
        neutts_group = self._create_neutts_settings()
        tts_settings_layout.addWidget(neutts_group)

        # Chatterbox FP16 Settings
        chatterbox_fp16_group = self._create_chatterbox_fp16_settings()
        tts_settings_layout.addWidget(chatterbox_fp16_group)

        # SopranoTTS Settings
        sopranotts_group = self._create_sopranotts_settings()
        tts_settings_layout.addWidget(sopranotts_group)

        # Qwen-TTS Settings
        qwen_tts_group = self._create_qwen_tts_settings()
        tts_settings_layout.addWidget(qwen_tts_group)

        scroll_layout.addWidget(tts_settings_card)

        # General Settings Section
        general_settings_card = CardWidget()
        general_settings_layout = QVBoxLayout(general_settings_card)
        general_title = SubtitleLabel("General Settings")
        general_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        general_settings_layout.addWidget(general_title)

        # VAD Settings
        vad_group = self._create_vad_settings()
        general_settings_layout.addWidget(vad_group)

        # LLM Settings
        llm_group = self._create_llm_settings()
        general_settings_layout.addWidget(llm_group)

        scroll_layout.addWidget(general_settings_card)

        # Save Settings Button
        save_layout = QHBoxLayout()
        self.save_settings_btn = PrimaryPushButton("Save Settings")
        self.save_settings_btn.clicked.connect(self.save_all_settings)
        save_layout.addWidget(self.save_settings_btn)
        save_layout.addStretch()
        scroll_layout.addLayout(save_layout)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        return page

    def _create_canary_settings(self):
        """Create Canary 1B v2 settings widget"""
        from qfluentwidgets import CardWidget

        group = CardWidget()

        layout = QVBoxLayout()

        # Provider selection
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(BodyLabel("Execution Provider:"))
        self.canary_provider_combo = ComboBox()
        self.canary_provider_combo.addItems(
            ["CPUExecutionProvider", "CUDAExecutionProvider"]
        )
        current_provider = (
            self.settings_manager.get("asr_settings", {})
            .get("canary-1b-v2", {})
            .get("provider", "CPUExecutionProvider")
        )
        index = self.canary_provider_combo.findText(current_provider)
        if index >= 0:
            self.canary_provider_combo.setCurrentIndex(index)
        provider_layout.addWidget(self.canary_provider_combo)
        provider_layout.addStretch()
        layout.addLayout(provider_layout)

        # Qwen-TTS supported languages (from inference.py)
        self.qwen_languages = [
            "Chinese",
            "English",
            "Japanese",
            "Korean",
            "German",
            "French",
            "Russian",
            "Portuguese",
            "Spanish",
            "Italian",
        ]

        # Overlap between Qwen-TTS and TTS models (these ASR can translate directly)
        # For others, we need LLM translation
        self.overlapping_languages = {
            "en": "English",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "de": "German",
            "fr": "French",
            "ru": "Russian",
            "pt": "Portuguese",
            "es": "Spanish",
            "it": "Italian",
        }

        # Language selection (source)
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(BodyLabel("Language:"))
        self.canary_language_combo = ComboBox()
        # All 25 languages supported by Canary-1b-v2
        languages = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic",
            "hi": "Hindi",
            "tr": "Turkish",
            "pl": "Polish",
            "nl": "Dutch",
            "sv": "Swedish",
            "da": "Danish",
            "no": "Norwegian",
            "fi": "Finnish",
            "el": "Greek",
            "he": "Hebrew",
            "th": "Thai",
            "vi": "Vietnamese",
            "id": "Indonesian",
            "cs": "Czech",
            "hu": "Hungarian",
        }
        for lang_code, lang_name in languages.items():
            self.canary_language_combo.addItem(lang_name, userData=lang_code)
        current_lang = (
            self.settings_manager.get("asr_settings", {})
            .get("canary-1b-v2", {})
            .get("language", "en")
        )
        index = self.canary_language_combo.findData(current_lang)
        if index >= 0:
            self.canary_language_combo.setCurrentIndex(index)
        lang_layout.addWidget(self.canary_language_combo)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)

        # Target Language (for translation)
        target_lang_layout = QHBoxLayout()
        target_lang_layout.addWidget(BodyLabel("Output Language:"))
        self.canary_target_language_combo = ComboBox()
        # All 25 languages supported by Canary-1b-v2
        target_languages = {
            "": "Same as input (no translation)",
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic",
            "hi": "Hindi",
            "tr": "Turkish",
            "pl": "Polish",
            "nl": "Dutch",
            "sv": "Swedish",
            "da": "Danish",
            "no": "Norwegian",
            "fi": "Finnish",
            "el": "Greek",
            "he": "Hebrew",
            "th": "Thai",
            "vi": "Vietnamese",
            "id": "Indonesian",
            "cs": "Czech",
            "hu": "Hungarian",
        }
        for lang_code, lang_name in target_languages.items():
            self.canary_target_language_combo.addItem(lang_name, userData=lang_code)
        current_target = (
            self.settings_manager.get("asr_settings", {})
            .get("canary-1b-v2", {})
            .get("target_language", "")
        )
        index = self.canary_target_language_combo.findData(current_target)
        if index >= 0:
            self.canary_target_language_combo.setCurrentIndex(index)
        target_lang_layout.addWidget(self.canary_target_language_combo)
        target_lang_layout.addStretch()
        layout.addLayout(target_lang_layout)

        group.setLayout(layout)
        return group

    def _create_parakeet_settings(self):
        """Create Parakeet TDT v3 settings widget"""
        from qfluentwidgets import CardWidget

        group = CardWidget()

        layout = QVBoxLayout()

        # Silence threshold
        silence_layout = QHBoxLayout()
        silence_layout.addWidget(BodyLabel("Silence Threshold:"))
        self.parakeet_silence_spin = SpinBox()
        self.parakeet_silence_spin.setRange(0, 1000)
        self.parakeet_silence_spin.setValue(
            int(
                self.settings_manager.get("asr_settings", {})
                .get("parakeet-tdt-v3", {})
                .get("silence_threshold", 0.001)
                * 1000
            )
        )
        self.parakeet_silence_spin.setSuffix(" (x0.001)")
        silence_layout.addWidget(self.parakeet_silence_spin)
        silence_layout.addStretch()
        layout.addLayout(silence_layout)

        # Min audio length
        min_length_layout = QHBoxLayout()
        min_length_layout.addWidget(BodyLabel("Min Audio Length:"))
        self.parakeet_min_length_spin = SpinBox()
        self.parakeet_min_length_spin.setRange(1, 10)
        self.parakeet_min_length_spin.setValue(
            int(
                self.settings_manager.get("asr_settings", {})
                .get("parakeet-tdt-v3", {})
                .get("min_audio_length", 1.0)
            )
        )
        self.parakeet_min_length_spin.setSuffix("s")
        min_length_layout.addWidget(self.parakeet_min_length_spin)
        min_length_layout.addStretch()
        layout.addLayout(min_length_layout)

        # Max audio length
        max_length_layout = QHBoxLayout()
        max_length_layout.addWidget(BodyLabel("Max Audio Length:"))
        self.parakeet_max_length_spin = SpinBox()
        self.parakeet_max_length_spin.setRange(1, 20)
        self.parakeet_max_length_spin.setValue(
            int(
                self.settings_manager.get("asr_settings", {})
                .get("parakeet-tdt-v3", {})
                .get("max_audio_length", 5.0)
            )
        )
        self.parakeet_max_length_spin.setSuffix("s")
        max_length_layout.addWidget(self.parakeet_max_length_spin)
        max_length_layout.addStretch()
        layout.addLayout(max_length_layout)

        group.setLayout(layout)
        return group

    def _create_neutts_settings(self):
        """Create NeuTTS-Nano settings widget"""
        from qfluentwidgets import CardWidget

        group = CardWidget()

        layout = QVBoxLayout()

        # Voice ID
        voice_layout = QHBoxLayout()
        voice_layout.addWidget(BodyLabel("Voice ID:"))
        self.neutts_voice_edit = LineEdit()
        self.neutts_voice_edit.setText(
            self.settings_manager.get("tts_settings", {})
            .get("neutts-nano", {})
            .get("voice_id", "default")
        )
        voice_layout.addWidget(self.neutts_voice_edit)
        voice_layout.addStretch()
        layout.addLayout(voice_layout)

        # Speed
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(BodyLabel("Speed:"))
        self.neutts_speed_spin = SpinBox()
        self.neutts_speed_spin.setRange(50, 200)
        self.neutts_speed_spin.setValue(
            int(
                self.settings_manager.get("tts_settings", {})
                .get("neutts-nano", {})
                .get("speed", 1.0)
                * 100
            )
        )
        self.neutts_speed_spin.setSuffix("%")
        speed_layout.addWidget(self.neutts_speed_spin)
        speed_layout.addStretch()
        layout.addLayout(speed_layout)

        # Pitch
        pitch_layout = QHBoxLayout()
        pitch_layout.addWidget(BodyLabel("Pitch:"))
        self.neutts_pitch_spin = SpinBox()
        self.neutts_pitch_spin.setRange(50, 200)
        self.neutts_pitch_spin.setValue(
            int(
                self.settings_manager.get("tts_settings", {})
                .get("neutts-nano", {})
                .get("pitch", 1.0)
                * 100
            )
        )
        self.neutts_pitch_spin.setSuffix("%")
        pitch_layout.addWidget(self.neutts_pitch_spin)
        pitch_layout.addStretch()
        layout.addLayout(pitch_layout)

        group.setLayout(layout)
        return group

    def _create_chatterbox_fp16_settings(self):
        """Create Chatterbox FP16 settings widget"""
        from qfluentwidgets import CardWidget

        group = CardWidget()

        layout = QVBoxLayout()

        # Language
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(BodyLabel("Language:"))
        self.chatterbox_fp16_language_combo = ComboBox()
        languages = {
            "ar": "Arabic",
            "da": "Danish",
            "de": "German",
            "el": "Greek",
            "en": "English",
            "es": "Spanish",
            "fi": "Finnish",
            "fr": "French",
            "he": "Hebrew",
            "hi": "Hindi",
            "it": "Italian",
            "ja": "Japanese",
            "ko": "Korean",
            "ms": "Malay",
            "nl": "Dutch",
            "no": "Norwegian",
            "pl": "Polish",
            "pt": "Portuguese",
            "ru": "Russian",
            "sv": "Swedish",
            "sw": "Swahili",
            "tr": "Turkish",
            "zh": "Chinese",
        }
        for lang_code, lang_name in languages.items():
            self.chatterbox_fp16_language_combo.addItem(lang_name, userData=lang_code)
        current_lang = (
            self.settings_manager.get("tts_settings", {})
            .get("chatterbox-fp16", {})
            .get("language", "en")
        )
        index = self.chatterbox_fp16_language_combo.findData(current_lang)
        if index >= 0:
            self.chatterbox_fp16_language_combo.setCurrentIndex(index)
        lang_layout.addWidget(self.chatterbox_fp16_language_combo)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)

        # Emotion Exaggeration
        exaggeration_layout = QHBoxLayout()
        exaggeration_layout.addWidget(BodyLabel("Emotion Exaggeration:"))
        self.chatterbox_fp16_exaggeration_spin = SpinBox()
        self.chatterbox_fp16_exaggeration_spin.setRange(0, 100)
        self.chatterbox_fp16_exaggeration_spin.setValue(
            int(
                self.settings_manager.get("tts_settings", {})
                .get("chatterbox-fp16", {})
                .get("exaggeration", 0.3)
                * 100
            )
        )
        self.chatterbox_fp16_exaggeration_spin.setSuffix("%")
        exaggeration_layout.addWidget(self.chatterbox_fp16_exaggeration_spin)
        exaggeration_layout.addStretch()
        layout.addLayout(exaggeration_layout)

        # CFG Weight
        cfg_layout = QHBoxLayout()
        cfg_layout.addWidget(BodyLabel("Classifier-Free Guidance Weight:"))
        self.chatterbox_fp16_cfg_spin = SpinBox()
        self.chatterbox_fp16_cfg_spin.setRange(0, 100)
        self.chatterbox_fp16_cfg_spin.setValue(
            int(
                self.settings_manager.get("tts_settings", {})
                .get("chatterbox-fp16", {})
                .get("cfg_weight", 0.1)
                * 100
            )
        )
        self.chatterbox_fp16_cfg_spin.setSuffix("%")
        cfg_layout.addWidget(self.chatterbox_fp16_cfg_spin)
        cfg_layout.addStretch()
        layout.addLayout(cfg_layout)

        # Temperature
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(BodyLabel("Temperature:"))
        self.chatterbox_fp16_temp_spin = SpinBox()
        self.chatterbox_fp16_temp_spin.setRange(0, 100)
        self.chatterbox_fp16_temp_spin.setValue(
            int(
                self.settings_manager.get("tts_settings", {})
                .get("chatterbox-fp16", {})
                .get("temperature", 0.8)
                * 100
            )
        )
        self.chatterbox_fp16_temp_spin.setSuffix("%")
        temp_layout.addWidget(self.chatterbox_fp16_temp_spin)
        temp_layout.addStretch()
        layout.addLayout(temp_layout)

        # Repetition Penalty
        penalty_layout = QHBoxLayout()
        penalty_layout.addWidget(BodyLabel("Repetition Penalty:"))
        self.chatterbox_fp16_penalty_spin = SpinBox()
        self.chatterbox_fp16_penalty_spin.setRange(100, 200)
        self.chatterbox_fp16_penalty_spin.setValue(
            int(
                self.settings_manager.get("tts_settings", {})
                .get("chatterbox-fp16", {})
                .get("repetition_penalty", 1.2)
                * 100
            )
        )
        self.chatterbox_fp16_penalty_spin.setSuffix("%")
        penalty_layout.addWidget(self.chatterbox_fp16_penalty_spin)
        penalty_layout.addStretch()
        layout.addLayout(penalty_layout)

        group.setLayout(layout)
        return group

    def _create_chatterbox_turbo_settings(self):
        """Create Chatterbox Turbo settings widget"""
        from qfluentwidgets import CardWidget

        group = CardWidget()

        layout = QVBoxLayout()

        # Max New Tokens
        tokens_layout = QHBoxLayout()
        tokens_layout.addWidget(BodyLabel("Max New Tokens:"))
        self.chatterbox_turbo_tokens_spin = SpinBox()
        self.chatterbox_turbo_tokens_spin.setRange(100, 2000)
        self.chatterbox_turbo_tokens_spin.setValue(
            self.settings_manager.get("tts_settings", {})
            .get("chatterbox-turbo", {})
            .get("max_new_tokens", 1024)
        )
        tokens_layout.addWidget(self.chatterbox_turbo_tokens_spin)
        tokens_layout.addStretch()
        layout.addLayout(tokens_layout)

        # Repetition Penalty
        penalty_layout = QHBoxLayout()
        penalty_layout.addWidget(BodyLabel("Repetition Penalty:"))
        self.chatterbox_turbo_penalty_spin = SpinBox()
        self.chatterbox_turbo_penalty_spin.setRange(100, 200)
        self.chatterbox_turbo_penalty_spin.setValue(
            int(
                self.settings_manager.get("tts_settings", {})
                .get("chatterbox-turbo", {})
                .get("repetition_penalty", 1.2)
                * 100
            )
        )
        self.chatterbox_turbo_penalty_spin.setSuffix("%")
        penalty_layout.addWidget(self.chatterbox_turbo_penalty_spin)
        penalty_layout.addStretch()
        layout.addLayout(penalty_layout)

        # Apply Watermark
        watermark_layout = QHBoxLayout()
        self.chatterbox_turbo_watermark_check = ToggleButton("Apply Watermark")
        self.chatterbox_turbo_watermark_check.setChecked(
            self.settings_manager.get("tts_settings", {})
            .get("chatterbox-turbo", {})
            .get("apply_watermark", False)
        )
        watermark_layout.addWidget(self.chatterbox_turbo_watermark_check)
        watermark_layout.addStretch()
        layout.addLayout(watermark_layout)

        group.setLayout(layout)
        return group

    def _create_qwen_tts_settings(self):
        """Create Qwen-TTS settings widget"""
        from qfluentwidgets import CardWidget

        group = CardWidget()

        layout = QVBoxLayout()

        # Speaker selection
        speaker_layout = QHBoxLayout()
        speaker_layout.addWidget(BodyLabel("Speaker:"))
        self.qwen_speaker_combo = ComboBox()
        speakers = ["Vivian", "XiaoYun", "Azure", "Cloud", "all"]
        for spk in speakers:
            self.qwen_speaker_combo.addItem(spk, userData=spk)
        current_speaker = (
            self.settings_manager.get("tts_settings", {})
            .get("qwen-tts", {})
            .get("speaker", "Vivian")
        )
        index = self.qwen_speaker_combo.findData(current_speaker)
        if index >= 0:
            self.qwen_speaker_combo.setCurrentIndex(index)
        speaker_layout.addWidget(self.qwen_speaker_combo)
        speaker_layout.addStretch()
        layout.addLayout(speaker_layout)

        # Language selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(BodyLabel("Language:"))
        self.qwen_language_combo = ComboBox()
        languages = [
            "Chinese",
            "English",
            "Japanese",
            "Korean",
            "French",
            "German",
            "Spanish",
        ]
        for lang in languages:
            self.qwen_language_combo.addItem(lang, userData=lang)
        current_lang = (
            self.settings_manager.get("tts_settings", {})
            .get("qwen-tts", {})
            .get("language", "Chinese")
        )
        index = self.qwen_language_combo.findData(current_lang)
        if index >= 0:
            self.qwen_language_combo.setCurrentIndex(index)
        lang_layout.addWidget(self.qwen_language_combo)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)

        # Streaming mode toggle
        streaming_layout = QHBoxLayout()
        streaming_layout.addWidget(BodyLabel("Streaming Mode:"))
        self.qwen_streaming_toggle = ToggleButton("")
        self.qwen_streaming_toggle.setChecked(
            not self.settings_manager.get("tts_settings", {})
            .get("qwen-tts", {})
            .get("non_streaming_mode", True)
        )
        self.qwen_streaming_toggle.setText(
            "Enabled" if self.qwen_streaming_toggle.isChecked() else "Disabled"
        )
        self.qwen_streaming_toggle.toggled.connect(
            lambda checked: self.qwen_streaming_toggle.setText(
                "Enabled" if checked else "Disabled"
            )
        )
        streaming_layout.addWidget(self.qwen_streaming_toggle)
        streaming_layout.addStretch()
        layout.addLayout(streaming_layout)

        # Instruction (optional)
        instruction_layout = QHBoxLayout()
        instruction_layout.addWidget(BodyLabel("Instruction:"))
        self.qwen_instruction_edit = LineEdit()
        self.qwen_instruction_edit.setText(
            self.settings_manager.get("tts_settings", {})
            .get("qwen-tts", {})
            .get("instruction", "")
        )
        self.qwen_instruction_edit.setPlaceholderText(
            "Optional style instruction (e.g., 'speak faster', 'happy tone')"
        )
        instruction_layout.addWidget(self.qwen_instruction_edit)
        instruction_layout.addStretch()
        layout.addLayout(instruction_layout)

        group.setLayout(layout)
        return group

    def _create_sopranotts_settings(self):
        """Create SopranoTTS settings widget"""
        from qfluentwidgets import CardWidget

        group = CardWidget()

        layout = QVBoxLayout()

        # Temperature
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(BodyLabel("Temperature:"))
        self.sopranotts_temp_spin = SpinBox()
        self.sopranotts_temp_spin.setRange(0, 100)
        self.sopranotts_temp_spin.setValue(
            int(
                self.settings_manager.get("tts_settings", {})
                .get("sopranotts", {})
                .get("temperature", 0.3)
                * 100
            )
        )
        self.sopranotts_temp_spin.setSuffix("%")
        temp_layout.addWidget(self.sopranotts_temp_spin)
        temp_layout.addStretch()
        layout.addLayout(temp_layout)

        # Top P
        top_p_layout = QHBoxLayout()
        top_p_layout.addWidget(BodyLabel("Top P:"))
        self.sopranotts_top_p_spin = SpinBox()
        self.sopranotts_top_p_spin.setRange(0, 100)
        self.sopranotts_top_p_spin.setValue(
            int(
                self.settings_manager.get("tts_settings", {})
                .get("sopranotts", {})
                .get("top_p", 0.95)
                * 100
            )
        )
        self.sopranotts_top_p_spin.setSuffix("%")
        top_p_layout.addWidget(self.sopranotts_top_p_spin)
        top_p_layout.addStretch()
        layout.addLayout(top_p_layout)

        # Repetition Penalty
        penalty_layout = QHBoxLayout()
        penalty_layout.addWidget(BodyLabel("Repetition Penalty:"))
        self.sopranotts_penalty_spin = SpinBox()
        self.sopranotts_penalty_spin.setRange(100, 200)
        self.sopranotts_penalty_spin.setValue(
            int(
                self.settings_manager.get("tts_settings", {})
                .get("sopranotts", {})
                .get("repetition_penalty", 1.2)
                * 100
            )
        )
        self.sopranotts_penalty_spin.setSuffix("%")
        penalty_layout.addWidget(self.sopranotts_penalty_spin)
        penalty_layout.addStretch()
        layout.addLayout(penalty_layout)

        group.setLayout(layout)
        return group

    def _create_vad_settings(self):
        """Create VAD settings widget"""
        from qfluentwidgets import CardWidget

        group = CardWidget()

        layout = QVBoxLayout()

        # Energy Threshold
        energy_layout = QHBoxLayout()
        energy_layout.addWidget(BodyLabel("Energy Threshold:"))
        self.vad_energy_spin = SpinBox()
        self.vad_energy_spin.setRange(1, 100)
        self.vad_energy_spin.setValue(
            int(self.settings_manager.get("energy_threshold", 0.02) * 1000)
        )
        self.vad_energy_spin.setSuffix(" (x0.001)")
        energy_layout.addWidget(self.vad_energy_spin)
        energy_layout.addStretch()
        layout.addLayout(energy_layout)

        # Silence Timeout
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(BodyLabel("Silence Timeout:"))
        self.vad_timeout_spin = SpinBox()
        self.vad_timeout_spin.setRange(100, 5000)
        self.vad_timeout_spin.setValue(
            self.settings_manager.get("silence_timeout_ms", 1000)
        )
        self.vad_timeout_spin.setSuffix("ms")
        timeout_layout.addWidget(self.vad_timeout_spin)
        timeout_layout.addStretch()
        layout.addLayout(timeout_layout)

        group.setLayout(layout)
        return group

    def _create_llm_settings(self):
        """Create LLM settings widget"""
        from qfluentwidgets import CardWidget

        group = CardWidget()

        layout = QVBoxLayout()

        # Groq API Key
        api_layout = QHBoxLayout()
        api_layout.addWidget(BodyLabel("Groq API Key:"))
        self.groq_api_edit = LineEdit()
        self.groq_api_edit.setText(self.settings_manager.get("groq_api_key", ""))
        self.groq_api_edit.setEchoMode(LineEdit.EchoMode.Password)
        api_layout.addWidget(self.groq_api_edit)
        api_layout.addStretch()
        layout.addLayout(api_layout)

        # Groq Model
        model_layout = QHBoxLayout()
        model_layout.addWidget(BodyLabel("Groq Model:"))
        self.groq_model_edit = LineEdit()
        self.groq_model_edit.setText(
            self.settings_manager.get("groq_model", "openai/gpt-oss-120b")
        )
        model_layout.addWidget(self.groq_model_edit)
        model_layout.addStretch()
        layout.addLayout(model_layout)

        # Tavily API Key
        tavily_layout = QHBoxLayout()
        tavily_layout.addWidget(BodyLabel("Tavily API Key:"))
        self.tavily_api_edit = LineEdit()
        self.tavily_api_edit.setText(self.settings_manager.get("tavily_api_key", ""))
        self.tavily_api_edit.setEchoMode(LineEdit.EchoMode.Password)
        tavily_layout.addWidget(self.tavily_api_edit)
        tavily_layout.addStretch()
        layout.addLayout(tavily_layout)

        group.setLayout(layout)
        return group

    def save_all_settings(self):
        """Save all settings"""
        try:
            # ASR Settings
            asr_settings = self.settings_manager.get("asr_settings", {})

            # Canary settings
            asr_settings["canary-1b-v2"] = {
                "provider": self.canary_provider_combo.currentData(),
                "language": self.canary_language_combo.currentData(),
                "target_language": self.canary_target_language_combo.currentData(),
            }

            # Parakeet settings
            asr_settings["parakeet-tdt-v3"] = {
                "silence_threshold": self.parakeet_silence_spin.value() / 1000.0,
                "min_audio_length": self.parakeet_min_length_spin.value(),
                "max_audio_length": self.parakeet_max_length_spin.value(),
            }

            # TTS Settings
            tts_settings = self.settings_manager.get("tts_settings", {})

            # NeuTTS settings
            tts_settings["neutts-nano"] = {
                "voice_id": self.neutts_voice_edit.text(),
                "speed": self.neutts_speed_spin.value() / 100.0,
                "pitch": self.neutts_pitch_spin.value() / 100.0,
            }

            # Chatterbox FP16 settings
            tts_settings["chatterbox-fp16"] = {
                "language": self.chatterbox_fp16_language_combo.currentData(),
                "exaggeration": self.chatterbox_fp16_exaggeration_spin.value() / 100.0,
                "cfg_weight": self.chatterbox_fp16_cfg_spin.value() / 100.0,
                "temperature": self.chatterbox_fp16_temp_spin.value() / 100.0,
                "repetition_penalty": self.chatterbox_fp16_penalty_spin.value() / 100.0,
            }

            # SopranoTTS settings
            tts_settings["sopranotts"] = {
                "temperature": self.sopranotts_temp_spin.value() / 100.0,
                "top_p": self.sopranotts_top_p_spin.value() / 100.0,
                "repetition_penalty": self.sopranotts_penalty_spin.value() / 100.0,
            }

            # Qwen-TTS settings
            tts_settings["qwen-tts"] = {
                "speaker": self.qwen_speaker_combo.currentData(),
                "language": self.qwen_language_combo.currentData(),
                "instruction": self.qwen_instruction_edit.text(),
                "non_streaming_mode": not self.qwen_streaming_toggle.isChecked(),
            }

            # General Settings
            self.settings_manager.set(
                "energy_threshold", self.vad_energy_spin.value() / 1000.0
            )
            self.settings_manager.set(
                "silence_timeout_ms", self.vad_timeout_spin.value()
            )
            self.settings_manager.set("groq_api_key", self.groq_api_edit.text())
            self.settings_manager.set("groq_model", self.groq_model_edit.text())
            self.settings_manager.set("tavily_api_key", self.tavily_api_edit.text())

            # Save settings
            self.settings_manager.set("asr_settings", asr_settings)
            self.settings_manager.set("tts_settings", tts_settings)
            self.settings_manager.save_settings()

            InfoBar.success(
                "Settings Saved",
                "All settings have been saved successfully",
                parent=self,
                duration=3000,
            )

        except Exception as e:
            InfoBar.error(
                "Save Error",
                f"Error saving settings: {str(e)}",
                parent=self,
                duration=5000,
            )

    def show_welcome_tip(self):
        """Show welcome teaching tip"""
        TeachingTip.create(
            target=self.main_page,
            icon=FluentIcon.HOME,
            title="Welcome to Canary Voice AI!",
            content="Press Ctrl+Space to start listening, or toggle Auto VAD for hands-free operation.",
            isClosable=True,
            tailPosition=TeachingTipTailPosition.BOTTOM,
            parent=self,
        )

    # Voice Cloning Methods
    def on_clone_tts_model_changed(self, index):
        """Handle voice cloning TTS model selection change"""
        model_id = self.clone_tts_combo.itemData(index)
        if model_id:
            # Update the main TTS model if it's a voice cloning capable model
            if model_id == "chatterbox-fp16":
                try:
                    self.tts_manager.switch_tts_model(model_id)
                    InfoBar.success(
                        "Voice Cloning Model",
                        f"Using {self.clone_tts_combo.currentText()} for voice cloning",
                        parent=self,
                        duration=2000,
                    )
                except Exception as e:
                    InfoBar.error(
                        "Model Error",
                        f"Failed to switch voice cloning model: {str(e)}",
                        parent=self,
                        duration=3000,
                    )

    def browse_reference_audio(self):
        """Browse for reference audio file"""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Reference Audio File",
            "",
            "Audio Files (*.wav *.mp3 *.m4a *.flac);;All Files (*.*)",
        )
        if file_path:
            self.ref_audio_path_edit.setText(file_path)
            # Save to settings
            voice_cloning_settings = self.settings_manager.get("voice_cloning", {})
            voice_cloning_settings["reference_audio_path"] = file_path
            self.settings_manager.set("voice_cloning", voice_cloning_settings)
            self.settings_manager.save_settings()

    def generate_cloned_voice(self):
        """Generate voice cloning audio"""
        text = self.clone_text_edit.toPlainText().strip()
        ref_audio_path = self.ref_audio_path_edit.text().strip()

        if not text:
            InfoBar.warning(
                "No Text",
                "Please enter text to synthesize",
                parent=self,
                duration=2000,
            )
            return

        if not ref_audio_path:
            InfoBar.warning(
                "No Reference Audio",
                "Please select a reference audio file",
                parent=self,
                duration=2000,
            )
            return

        if not os.path.exists(ref_audio_path):
            InfoBar.error(
                "File Not Found",
                "Reference audio file not found",
                parent=self,
                duration=2000,
            )
            return

        # Start progress
        self.clone_progress_ring.setVisible(True)
        self.clone_generate_btn.setEnabled(False)

        # Run voice cloning in background thread
        import threading

        thread = threading.Thread(
            target=self._generate_cloned_voice_thread, args=(text, ref_audio_path)
        )
        thread.start()

    def _generate_cloned_voice_thread(self, text: str, ref_audio_path: str):
        """Background thread for voice cloning generation"""
        try:
            model_id = self.clone_tts_combo.currentData()
            language = self.clone_language_combo.currentData()

            if model_id == "chatterbox-fp16":
                exaggeration = self.exaggeration_spin.value() / 100.0
                temperature = self.temperature_spin.value() / 100.0

                audio = self.tts_manager.generate_speech(
                    text,
                    ref_audio_path,
                    language=language,
                    exaggeration=exaggeration,
                    temperature=temperature,
                )

            elif model_id == "chatterbox-turbo":
                audio = self.tts_manager.generate_speech(
                    text, ref_audio_path, max_new_tokens=1024, repetition_penalty=1.2
                )
            else:
                raise ValueError(f"Voice cloning not supported for {model_id}")

            # Store generated audio
            self.cloned_audio_data = audio
            self.cloned_audio_sample_rate = 24000

            # Update UI
            self.clone_audio_info.setText(
                f"Generated audio: {len(audio)} samples ({len(audio) / 24000:.2f}s)"
            )

            # Enable buttons
            self.clone_play_btn.setEnabled(True)
            self.clone_save_btn.setEnabled(True)

            InfoBar.success(
                "Voice Cloning Complete",
                f"Successfully generated cloned voice audio",
                parent=self,
                duration=3000,
            )

        except Exception as e:
            InfoBar.error(
                "Voice Cloning Failed",
                f"Error generating cloned voice: {str(e)}",
                parent=self,
                duration=5000,
            )

        finally:
            # Hide progress and re-enable button
            self.clone_progress_ring.setVisible(False)
            self.clone_generate_btn.setEnabled(True)

    def play_cloned_voice(self):
        """Play the generated cloned voice audio"""
        if self.cloned_audio_data is not None and len(self.cloned_audio_data) > 0:
            try:
                self.tts_manager.play_audio(
                    self.cloned_audio_data, self.cloned_audio_sample_rate
                )
                InfoBar.info(
                    "Playing Audio",
                    "Playing cloned voice audio",
                    parent=self,
                    duration=2000,
                )
            except Exception as e:
                InfoBar.error(
                    "Playback Error",
                    f"Error playing audio: {str(e)}",
                    parent=self,
                    duration=3000,
                )

    def save_cloned_voice(self):
        """Save the generated cloned voice audio"""
        if self.cloned_audio_data is not None and len(self.cloned_audio_data) > 0:
            from PySide6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Cloned Voice Audio",
                "cloned_voice.wav",
                "WAV Files (*.wav);;All Files (*.*)",
            )
            if file_path:
                try:
                    import soundfile as sf

                    sf.write(
                        file_path, self.cloned_audio_data, self.cloned_audio_sample_rate
                    )
                    InfoBar.success(
                        "Audio Saved",
                        f"Cloned voice saved to {os.path.basename(file_path)}",
                        parent=self,
                        duration=3000,
                    )
                except Exception as e:
                    InfoBar.error(
                        "Save Error",
                        f"Error saving audio: {str(e)}",
                        parent=self,
                        duration=3000,
                    )


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
