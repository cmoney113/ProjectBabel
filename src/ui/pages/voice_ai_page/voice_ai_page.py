"""
Voice AI Page - Main voice processing interface

Refactored modular architecture:
- Widgets: RecordingControls, ModelSelectors, TranscriptionPanel, ResponsePanel, ModeControls
- Handlers: ModelHandlers, RecordingHandlers, UIHandlers
- Services: TextProcessorService, TTSService
- State: StateManager with VoiceAIState

This file coordinates all components and maintains backward compatibility.
"""

import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, Signal, Slot
from qfluentwidgets import (
    SubtitleLabel,
    BodyLabel,
    IndeterminateProgressRing,
    InfoBar,
    TransparentToolButton,
    FluentIcon,
)

from src.chat_sidebar import ChatSidebar
from .state import StateManager, VoiceAIState
from .widgets import (
    RecordingControlsWidget,
    ModelSelectorsWidget,
    TranscriptionPanelWidget,
    ResponsePanelWidget,
    ModeControlsWidget,
)
from .handlers import ModelHandlers, RecordingHandlers, UIHandlers
from .services import TextProcessorService, TTSService

logger = logging.getLogger(__name__)


class VoiceAIPage(QWidget):
    """
    Main voice AI processing page with recording controls and displays.

    This is now a coordinator class that:
    - Owns and layouts sub-widgets
    - Connects signals between components
    - Exposes public API for MainWindow interaction
    - Maintains backward compatibility with existing code

    Signal Contracts:
    =================
    # Emitted by this widget
    start_listening_requested = Signal()
    stop_listening_requested = Signal()
    manual_activation_requested = Signal()

    # Received from sub-widgets (internal)
    - RecordingControlsWidget: start_clicked, stop_clicked, sensitivity_changed
    - ModelSelectorsWidget: asr_model_changed, tts_model_changed
    - TranscriptionPanelWidget: custom_text_toggled, play_text_requested
    - ResponsePanelWidget: verbosity_changed, translation_toggled
    - ModeControlsWidget: mode_toggled, window_selected
    """

    # Signals for communication with main window (backward compatible)
    start_listening_requested = Signal()
    stop_listening_requested = Signal()
    manual_activation_requested = Signal()

    def __init__(self, main_window):
        super().__init__()
        self.setObjectName("VoiceAIPage")
        self.main_window = main_window

        # Get references to managers
        self.settings_manager = main_window.get_settings_manager()
        self.chat_session_manager = main_window.get_chat_session_manager()
        self.voice_processor = main_window.get_voice_processor()
        self.tts_manager = main_window.get_tts_manager()

        # Event tracking for ASR/TTS coordination
        self.current_event_id = None

        # Initialize state manager
        self.state_manager = StateManager(self.settings_manager)
        self.state_manager.load_from_settings()

        # Initialize services
        self.text_processor = TextProcessorService(self.settings_manager)
        self.tts_service = TTSService(
            self.tts_manager, self.settings_manager, self.main_window
        )

        # Initialize handlers
        self.model_handlers = ModelHandlers(
            self.voice_processor, self.tts_manager, self.settings_manager, self
        )
        self.recording_handlers = RecordingHandlers(
            self.voice_processor, self.main_window, self
        )
        self.ui_handlers = UIHandlers(
            self.state_manager, self.settings_manager, parent=self
        )

        # Initialize UI components (created after handlers for signal connections)
        self._init_ui()
        self._connect_signals()

        # Connect recording handler signals to UI updates
        self._connect_recording_signals()

    def _init_ui(self):
        """Initialize the user interface with modular widgets"""
        # Main horizontal layout: sidebar + content
        page_layout = QHBoxLayout(self)
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
        header_layout = self._create_header_layout()
        content_layout.addLayout(header_layout)

        # Horizontal container for recording controls + model selectors
        controls_container = QWidget()
        controls_h_layout = QHBoxLayout(controls_container)
        controls_h_layout.setContentsMargins(0, 0, 0, 0)
        controls_h_layout.setSpacing(20)

        # Recording controls and waveform (left side)
        self.recording_controls = RecordingControlsWidget(self.tts_manager, self)
        controls_h_layout.addWidget(self.recording_controls, 1)  # stretch factor 1

        # Convenience property for dictation_toggle
        self.dictation_toggle = self.recording_controls.dictation_toggle

        # Model selectors (right side)
        self.model_selectors = ModelSelectorsWidget(
            self.voice_processor, self.tts_manager, self.recording_controls, self
        )
        controls_h_layout.addWidget(self.model_selectors, 1)  # stretch factor 1

        content_layout.addWidget(controls_container)

        # Progress indicator
        self.progress_ring = IndeterminateProgressRing()
        self.progress_ring.setVisible(False)
        content_layout.addWidget(
            self.progress_ring, alignment=Qt.AlignmentFlag.AlignCenter
        )

        # Transcription display
        self.transcription_panel = TranscriptionPanelWidget(self)
        content_layout.addWidget(self.transcription_panel)

        # Response display
        self.response_panel = ResponsePanelWidget(self)
        content_layout.addWidget(self.response_panel)

        content_layout.addStretch()

        # Add content layout to page layout
        page_layout.addLayout(content_layout, 1)

        # Store waveform widget reference for UI handler
        self.ui_handlers.waveform_widget = self.recording_controls.waveform_widget

    def _create_header_layout(self) -> QHBoxLayout:
        """Create header with title and mini mode button"""
        layout = QHBoxLayout()

        title = SubtitleLabel("Canary Voice AI Assistant")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        layout.addWidget(title)

        # Mini mode button
        self.mini_mode_button = TransparentToolButton(FluentIcon.PIN, self)
        self.mini_mode_button.setToolTip("Toggle Mini Mode")
        self.mini_mode_button.clicked.connect(self._toggle_mini_mode)
        layout.addWidget(self.mini_mode_button)

        layout.addStretch()
        return layout

    def _connect_signals(self):
        """Connect all widget signals to handlers"""
        # Recording controls
        self.recording_controls.start_clicked.connect(
            self.recording_handlers.start_listening
        )
        self.recording_controls.stop_clicked.connect(
            self.recording_handlers.stop_listening
        )
        self.recording_controls.sensitivity_changed.connect(
            self.ui_handlers.on_sensitivity_changed
        )
        self.recording_controls.auto_vad_toggled.connect(
            self.ui_handlers.on_auto_vad_toggled
        )

        # Model selectors
        self.model_selectors.asr_model_changed.connect(
            lambda model_id: self.model_handlers.on_asr_model_changed(
                model_id, self.model_selectors.asr_model_combo.currentText()
            )
        )
        self.model_selectors.tts_model_changed.connect(
            lambda model_id: self.model_handlers.on_tts_model_changed(
                model_id,
                self.model_selectors.tts_model_combo.currentText(),
                self.model_selectors.get_kittentts_voice()
                if model_id == "kittentts"
                else None,
                self.model_selectors.get_vibevoice_voice()
                if model_id == "vibevoice"
                else None,
            )
        )
        self.model_selectors.kittentts_voice_changed.connect(
            self.model_handlers.on_kittentts_voice_changed
        )
        self.model_selectors.vibevoice_voice_changed.connect(
            lambda voice: self.model_handlers.on_vibevoice_voice_changed(
                voice, self.state_manager.state.vibevoice_language
            )
        )

        # Transcription panel
        self.transcription_panel.custom_text_toggled.connect(
            self.ui_handlers.on_custom_text_toggled
        )
        self.transcription_panel.play_text_requested.connect(
            self._on_play_text_requested
        )

        # Response panel
        self.response_panel.verbosity_changed.connect(
            self.ui_handlers.on_verbosity_changed
        )
        self.response_panel.translation_toggled.connect(
            self.ui_handlers.on_translation_toggled
        )
        self.response_panel.target_language_changed.connect(
            self.ui_handlers.on_target_language_changed
        )

        # Mode controls (now in ModelSelectorsWidget)
        self.model_selectors.dictation_mode_changed.connect(
            self.ui_handlers.on_mode_toggled
        )
        self.model_selectors.window_selected.connect(
            self.ui_handlers.on_window_selected
        )

    def _connect_recording_signals(self):
        """Connect recording handler signals to UI updates"""
        self.recording_handlers.recording_started.connect(self._on_recording_started)
        self.recording_handlers.recording_stopped.connect(self._on_recording_stopped)
        self.recording_handlers.processing_started.connect(self.on_processing_started)
        self.recording_handlers.processing_finished.connect(self.on_processing_finished)
        self.recording_handlers.error_occurred.connect(self._on_error)

    # === Recording State Updates ===

    def _on_recording_started(self):
        """Handle recording started"""
        self.recording_controls.set_listening_state(True)
        InfoBar.info(
            "Listening Started",
            "Speak your query/dictation - unlimited duration supported",
            parent=self,
            duration=2000,
        )

    def _on_recording_stopped(self):
        """Handle recording stopped"""
        self.recording_controls.set_listening_state(False)

    def _on_error(self, title: str, message: str):
        """Handle error from recording handlers"""
        InfoBar.error(title, message, parent=self, duration=3000)

    # === Public API (Backward Compatible) ===

    def manual_activate(self):
        """Manually activate listening"""
        self.recording_handlers.manual_activate(
            self.state_manager.state.auto_vad_enabled
        )

    def start_listening(self):
        """Start listening (called from hotkey)"""
        self.recording_handlers.start_listening()

    def stop_listening(self):
        """Stop listening (called from hotkey)"""
        self.recording_handlers.stop_listening()


    def update_transcription(self, text: str):
        """Update transcription display and save to session"""
        # Create new event in both panels if this is a new transcription
        # This links the ASR (top) and TTS (bottom) boxes together
        if self.current_event_id is None:
            # Generate event ID from current timestamp
            from datetime import datetime
            self.current_event_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create event in ASR panel (top box)
            self.transcription_panel.create_event(self.current_event_id)
            
            # Create matching event in TTS panel (bottom box) with same timestamp
            asr_event = self.transcription_panel.events.get(self.current_event_id)
            if asr_event:
                self.response_panel.create_event(self.current_event_id, asr_event.timestamp)
            else:
                self.response_panel.create_event(self.current_event_id)
        
        # Add transcription to ASR panel (top box)
        self.transcription_panel.append_transcription(text, self.current_event_id)

        # Save to chat session
        if text.strip():
            session = self.chat_session_manager.get_current_session()
            if session:
                session.add_message("user", text)

    def update_response(self, text: str):
        """Update response display with markdown"""
        # Use the same event_id to link with the transcription
        # This ensures the processed result appears in the same "conversation" as the raw input
        event_id = self.current_event_id
        
        # If no event exists (shouldn't happen normally), create one
        if event_id is None:
            from datetime import datetime
            event_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_event_id = event_id
            self.transcription_panel.create_event(event_id)
            asr_event = self.transcription_panel.events.get(event_id)
            timestamp = asr_event.timestamp if asr_event else None
            self.response_panel.create_event(event_id, timestamp)
        
        # Add response to TTS panel (bottom box) - uses same event_id
        self.response_panel.append_response(text, event_id)

        # Save to chat session
        session = self.chat_session_manager.get_current_session()
        if session:
            session.add_message("assistant", text)


    def update_recording_timer(self):
        """Update the recording timer display"""
        elapsed = self.recording_handlers.get_elapsed_time()
        self.recording_controls.update_timer(elapsed)

    def on_processing_started(self):
        """Handle processing started event"""
        self.progress_ring.setVisible(True)
        self.recording_controls.set_processing_state(True)

    def on_processing_finished(self):
        """Handle processing finished event"""
        self.progress_ring.setVisible(False)
        self.recording_controls.set_processing_state(False)

    # === Getters (Backward Compatible) ===

    def get_kittentts_voice(self) -> str:
        """Get selected KittenTTS voice"""
        return self.model_selectors.get_kittentts_voice()

    def get_vibevoice_voice(self) -> str:
        """Get selected VibeVoice voice"""
        return self.model_selectors.get_vibevoice_voice()

    def get_dictation_mode(self) -> bool:
        """Get current dictation mode state"""
        return self.model_selectors.is_dictation_mode()

    def get_verbosity(self) -> str:
        """Get current verbosity level"""
        return self.state_manager.state.verbosity

    def get_translation_enabled(self) -> bool:
        """Get translation enabled state"""
        return self.state_manager.state.translation_enabled

    def get_target_language(self) -> str:
        """Get target language code"""
        return self.state_manager.state.target_language

    def get_dictation_window_id(self) -> str | None:
        """Get selected window ID for dictation"""
        return self.model_selectors.get_selected_window_id()

    # === Private Methods ===

    def _toggle_mini_mode(self):
        """Toggle mini mode via main window"""
        self.main_window.toggle_mini_mode()

    def _on_session_selected(self, session_id: str):
        """Handle session selection from sidebar"""
        # Reset event tracking for new session
        self.current_event_id = None
        
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
                    self.response_panel.set_response(msg.get("content", ""))
                    break
        else:
            self.response_panel.clear_response()
            self.transcription_panel.clear_transcription()
            if hasattr(self.main_window, "voice_worker"):
                self.main_window.voice_worker.conversation_history = []

        self.chat_sidebar.refresh_session_list()

    def _on_new_chat(self):
        """Handle new chat request"""
        # Reset event tracking for new conversation
        self.current_event_id = None
        
        self.response_panel.clear_response()
        self.transcription_panel.clear_transcription()
        if hasattr(self.main_window, "voice_worker"):
            self.main_window.voice_worker.conversation_history = []

        self.chat_session_manager.create_new_session()
        self.chat_sidebar.refresh_session_list()

    def _on_play_text_requested(self, text: str):
        """
        Handle play text request from transcription panel

        Routes to appropriate handler based on text type:
        - URL: Fetch and speak content
        - Search query: Run search and show results
        - Plain text: Speak directly
        """
        text_type = self.text_processor.classify_text_input(text)

        if text_type == "url":
            normalized_url = self.text_processor.normalize_url(text)
            self._process_url_and_speak(normalized_url)
        elif text_type == "search":
            self._run_web_search_and_show_results(text)
        else:
            self._speak_text(text)

    def _process_url_and_speak(self, url: str, title: str = None):
        """Process URL through archive.is and speak"""

        def progress_callback(msg: str):
            self.transcription_panel.append_transcription(msg)

        result = self.text_processor.process_url(url, progress_callback)
        if result and result.get("content"):
            content = result["content"]
            article_title = result.get("title", title or "Article")

            # Display preview
            self.transcription_panel.append_transcription(
                f"📰 {article_title}\n{content[:500]}..."
            )

            # Speak the content
            self._speak_text(content)
        else:
            self.transcription_panel.append_transcription("⚠️ No content extracted")

    def _run_web_search_and_show_results(self, query: str, max_results: int = 5):
        """Run web search and show results dialog"""
        results = self.text_processor.run_web_search(query, max_results)

        if not results:
            InfoBar.warning(
                "No Results",
                "No search results found",
                parent=self,
                duration=2000,
            )
            return

        self._show_search_results_dialog(query, results)

    def _speak_text(self, text: str):
        """Synthesize and play text via TTS"""
        if not text:
            return

        tts_model = self.settings_manager.get("tts_model", "kittentts")
        streaming = self.settings_manager.get("tts_streaming", False)

        voice = None
        language = None
        if tts_model == "vibevoice":
            voice = self.settings_manager.get("vibevoice_voice", "Carter")
            language = self.settings_manager.get("vibevoice_language", "en")

        try:
            self.tts_service.synthesize_and_play(
                text,
                model=tts_model,
                voice=voice,
                language=language,
                streaming=streaming,
            )
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            self.transcription_panel.append_transcription(f"❌ TTS failed: {e}")

    def _show_search_results_dialog(self, query: str, results: list):
        """Show search results in a dialog for user to select"""
        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QListWidget,
            QListWidgetItem,
            QLabel,
            QPushButton,
            QHBoxLayout,
        )
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

            item_text = f"{i + 1}. {title}\n   {url}\n   {content}"
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
                self._process_url_and_speak(url, title)

        select_btn = QPushButton("Read Selected")
        select_btn.clicked.connect(on_select)
        btn_layout.addWidget(select_btn)

        layout.addLayout(btn_layout)

        # Double-click to select
        list_widget.itemDoubleClicked.connect(on_select)

        dialog.exec()
