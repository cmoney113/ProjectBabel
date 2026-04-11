"""
Main Window - Main application window with Fluent UI
Orchestrates all UI components and manages the application state
"""

import sys
import os
import json
import threading
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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
from src.settings_manager import SettingsManager
from src.enhanced_voice_processor import EnhancedVoiceProcessor
from src.llm_manager import LLMManager
from src.tts_manager import TTSManager
from src.web_search import WebSearchManager
from src.chat_session_manager import ChatSessionManager
from src.chat_sidebar import ChatSidebar
from src.markdown_display import MarkdownDisplay, ScrollableMarkdownDisplay
from src.languages import CANARY_LANGUAGES, TTS_MODELS, get_tts_languages
from src.ui.pages.voice_ai_page import VoiceAIPage
from src.ui.pages.voice_cloning_page import VoiceCloningPage
from src.ui.pages.gtt_page import GTTPage
from src.ui.pages.settings_page import SettingsPage
from src.ui.pages.projects_page import ProjectsPage
from src.workers.voice_ai_worker import VoiceAIWorker
from src.porcupine_manager import WakeWordManager


class MainWindow(FluentWindow):
    """Main application window with Fluent UI - orchestrates all components"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Canary Voice AI Assistant")
        self.setMinimumSize(800, 600)
        self.resize(1200, 800)

        # Mini-mode state
        self.is_mini_mode = False
        self.normal_geometry = None

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

        # Wake word manager
        self.wakeword_manager = WakeWordManager()
        self.wakeword_active = False

        # Initialize timers
        self.recording_timer = QTimer(self)
        self.recording_timer.timeout.connect(self.update_recording_timer)
        self.recording_start_time = 0

        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Initialize UI components
        self.init_ui()
        self.init_mini_mode_button()
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

    def start_wakeword_listening(self, is_dictation=False):
        """Start listening for wake word"""
        self.wakeword_manager.set_error_callback(self._on_wakeword_error)

        if is_dictation:
            self.wakeword_manager.start_dictation_mode(self._on_wakeword_triggered)
        else:
            self.wakeword_manager.start_voice_ai_mode(self._on_wakeword_triggered)
        self.wakeword_active = True

    def _on_wakeword_error(self, error_msg):
        """Called when wake word has an error"""
        print(f"Wake word error: {error_msg}")
        if hasattr(self, "mini_page") and self.mini_page:
            self.mini_page.on_wakeword_error(error_msg)

    def stop_wakeword_listening(self):
        """Stop wake word listening"""
        self.wakeword_manager.stop_all()
        self.wakeword_active = False

    def _on_wakeword_triggered(self):
        """Called when wake word is detected"""
        print("Wake word detected!")
        if hasattr(self, "mini_page") and self.mini_page:
            self.mini_page.on_wakeword_detected()
        elif hasattr(self, "voice_ai_page") and self.voice_ai_page:
            self.voice_ai_page.start_listening()

    def init_ui(self):
        """Initialize the user interface"""
        # Create pages
        self.voice_ai_page = VoiceAIPage(self)
        self.voice_cloning_page = VoiceCloningPage(self)
        self.gtt_page = GTTPage(self)
        self.projects_page = ProjectsPage(self)
        self.settings_page = SettingsPage(self)

        # Add navigation items
        self.addSubInterface(self.voice_ai_page, FluentIcon.HOME, "Voice AI")
        self.addSubInterface(
            self.voice_cloning_page, FluentIcon.MICROPHONE, "Voice Cloning"
        )
        self.addSubInterface(self.gtt_page, FluentIcon.ROBOT, "GTT Automation")
        self.addSubInterface(self.projects_page, FluentIcon.FOLDER, "Projects")
        self.addSubInterface(self.settings_page, FluentIcon.SETTING, "Settings")

    def init_mini_mode_button(self):
        """Add mini-mode button to Voice AI page"""
        self.mini_mode_button = TransparentToolButton(FluentIcon.PIN, self)
        self.mini_mode_button.setToolTip("Toggle Mini Mode")
        self.mini_mode_button.clicked.connect(self.toggle_mini_mode)

    def init_workers(self):
        """Initialize background workers"""
        self.voice_worker = VoiceAIWorker(
            self.voice_processor,
            self.llm_manager,
            self.tts_manager,
            self.web_search_manager,
            self.settings_manager,
        )
        self.voice_worker.transcription_ready.connect(self.on_transcription_ready)
        self.voice_worker.response_ready.connect(self.on_response_ready)
        self.voice_worker.processing_started.connect(self.on_processing_started)
        self.voice_worker.processing_finished.connect(self.on_processing_finished)
        self.voice_worker.error_occurred.connect(self.on_error)

    def init_shortcuts(self):
        """Initialize keyboard shortcuts"""
        self.hotkey_shortcut = QShortcut(QKeySequence("Ctrl+Space"), self)
        self.hotkey_shortcut.activated.connect(self.manual_activate)

    # === Event Handlers ===

    def on_transcription_ready(self, text):
        """Handle transcription ready signal"""
        # Forward to current page for display
        if hasattr(self.voice_ai_page, "update_transcription"):
            self.voice_ai_page.update_transcription(text)

    def on_response_ready(self, text):
        """Handle response ready signal"""
        # Forward to current page for display
        if hasattr(self.voice_ai_page, "update_response"):
            self.voice_ai_page.update_response(text)

    def on_processing_started(self):
        """Handle processing started"""
        # Forward to current page
        if hasattr(self.voice_ai_page, "on_processing_started"):
            self.voice_ai_page.on_processing_started()

    def on_processing_finished(self):
        """Handle processing finished"""
        # Forward to current page
        if hasattr(self.voice_ai_page, "on_processing_finished"):
            self.voice_ai_page.on_processing_finished()

    def on_error(self, error_message):
        """Handle error signal"""
        from qfluentwidgets import InfoBar

        InfoBar.error("Error", error_message, parent=self, duration=5000)

    # === Public Methods ===

    def get_voice_processor(self):
        """Get voice processor instance"""
        return self.voice_processor

    def get_chat_session_manager(self):
        """Get chat session manager"""
        return self.chat_session_manager

    def get_settings_manager(self):
        """Get settings manager"""
        return self.settings_manager

    def get_tts_manager(self):
        """Get TTS manager instance"""
        return self.tts_manager

    def get_voice_worker(self):
        """Get voice worker instance"""
        return self.voice_worker

    def manual_activate(self):
        """Manually activate listening"""
        # Forward to voice AI page
        if hasattr(self.voice_ai_page, "manual_activate"):
            self.voice_ai_page.manual_activate()

    def update_recording_timer(self):
        """Update recording timer (forwarded from voice AI page)"""
        if hasattr(self.voice_ai_page, "update_recording_timer"):
            self.voice_ai_page.update_recording_timer()

    def start_listening(self):
        """Start listening (forwarded from voice AI page)"""
        if hasattr(self.voice_ai_page, "start_listening"):
            self.voice_ai_page.start_listening()

    def stop_listening(self):
        """Stop listening (forwarded from voice AI page)"""
        if hasattr(self.voice_ai_page, "stop_listening"):
            self.voice_ai_page.stop_listening()

    def process_audio(self, audio_data):
        """Process audio data (forwarded from voice AI page)"""
        self.voice_worker.set_audio(audio_data)

        is_dictation = self.voice_ai_page.get_dictation_mode()
        self.voice_worker.set_dictation_mode(is_dictation)

        # Auto-select second-to-last window for dictation
        window_id = self.voice_ai_page.get_dictation_window_id()
        if is_dictation and window_id is None:
            windows = self.tts_manager.get_window_list()
            if len(windows) >= 2:
                window_id = windows[1].get("id")

        self.voice_worker.set_dictation_window(window_id)
        self.voice_worker.set_verbosity(self.voice_ai_page.get_verbosity())

        # Set translation parameters
        target_lang = (
            self.voice_ai_page.get_target_language()
            if self.voice_ai_page.get_translation_enabled()
            else ""
        )
        self.voice_worker.set_target_language(target_lang)
        self.voice_worker.set_translation_enabled(
            self.voice_ai_page.get_translation_enabled()
        )

        # Set current TTS model
        current_tts = self.tts_manager.get_current_tts_model()
        self.voice_worker.set_tts_model(current_tts)

        # Set KittenTTS voice if using KittenTTS
        if current_tts == "kittentts":
            kittentts_voice = self.voice_ai_page.get_kittentts_voice()
            self.voice_worker.set_tts_voice(kittentts_voice)

        self.voice_worker.start()

    def show_welcome_tip(self):
        """Show welcome teaching tip"""
        from qfluentwidgets import TeachingTip

        TeachingTip.create(
            target=self.navigationInterface,
            icon=FluentIcon.HOME,
            title="Welcome to Canary Voice AI!",
            content="Press Ctrl+Space to start listening, or toggle Auto VAD for hands-free operation.",
            isClosable=True,
            tailPosition=TeachingTipTailPosition.BOTTOM,
            parent=self,
        )

    def toggle_mini_mode(self):
        """Toggle between normal and mini-mode"""
        if self.is_mini_mode:
            self.exit_mini_mode()
        else:
            self.enter_mini_mode()

    def enter_mini_mode(self):
        """Enter mini-mode: compact overlay window"""
        from PySide6.QtCore import Qt
        from src.ui.pages.mini_mode_page import MiniModePage

        self.is_mini_mode = True
        self.normal_geometry = self.geometry()

        # Save and hide main window
        self.hide()

        # Create mini page and dialog
        self.mini_page = MiniModePage(self)
        self.mini_dialog = self.mini_page.create_dialog(None)
        self.mini_dialog.setWindowTitle('Voice AI - Mini Mode')
        
        # Connect signals
        self.voice_worker.transcription_ready.connect(
            self.mini_page.on_transcription_ready
        )
        self.voice_worker.response_ready.connect(self.mini_page.on_response_ready)
        self.voice_worker.processing_started.connect(
            self.mini_page.on_processing_started
        )
        self.voice_worker.processing_finished.connect(
            self.mini_page.on_processing_finished
        )

        # Update button icon
        if hasattr(self, "mini_mode_button"):
            self.mini_mode_button.setIcon(FluentIcon.UNPIN)

        # Show and resize mini dialog
        self.mini_dialog.show()
        self.mini_dialog.resize(450, 350)

    def exit_mini_mode(self):
        """Exit mini-mode: restore normal window"""
        self.is_mini_mode = False

        if hasattr(self, "mini_dialog") and self.mini_dialog:
            self.mini_dialog.close()
            self.mini_dialog = None
        self.mini_page = None

        self.setWindowFlags(Qt.WindowType.Window)
        if self.normal_geometry:
            self.setGeometry(self.normal_geometry)

        self.setStyleSheet("""
            QMainWindow, FluentWindow {
                background-color: #0a0f1d;
            }
        """)

        self.navigationInterface.show()
        self.show()

        if hasattr(self, "mini_mode_button"):
            self.mini_mode_button.setIcon(FluentIcon.PIN)


