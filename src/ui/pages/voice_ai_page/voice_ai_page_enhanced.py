"""
Enhanced Voice AI Page with Modern UI and Improved Handling

Integrates:
- Conversation context system with rolling summaries
- Enhanced response panel with ChatGPT-like interface
- Improved transcription panel with better scroll logic
- Fixed hardcoded minimum size constraints
- Modern chat/dictation capabilities
"""

import logging
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer

from qfluentwidgets import (
    CardWidget, BodyLabel, PushButton, ComboBox, SwitchButton,
    InfoBar, FluentIcon, TransparentToolButton
)

# Import new enhanced components
from .widgets.enhanced_response_panel import EnhancedResponsePanel
from .widgets.enhanced_transcription_panel import EnhancedTranscriptionPanel
from .widgets.recording_controls import RecordingControlsWidget
from .widgets.model_selectors import ModelSelectorsWidget
# from .widgets.mode_controls import ModeControlsWidget  # Integrated into ModelSelectorsWidget

# Import conversation context system
from ....conversation_context import ConversationContextManager, AdvancedConversationManager

logger = logging.getLogger(__name__)


class EnhancedVoiceAIPage(QWidget):
    """
    Enhanced Voice AI page with modern UI and improved handling
    """

    # Signals (backward compatible)
    start_listening_requested = Signal()
    stop_listening_requested = Signal()
    manual_activation_requested = Signal()

    def __init__(
        self,
        session_manager,
        settings_manager,
        voice_processor,
        tts_manager,
        llm_manager,
        parent=None
    ):
        super().__init__(parent)
        
        # Store dependencies
        self.session_manager = session_manager
        self.settings_manager = settings_manager
        self.voice_processor = voice_processor
        self.tts_manager = tts_manager
        self.llm_manager = llm_manager
        
        # Initialize conversation context
        self.conversation_context = ConversationContextManager()
        self.advanced_context = AdvancedConversationManager(self.conversation_context)
        
        # Current conversation state
        self.current_session_id = None
        
        self._init_ui()
        self._connect_signals()
        self._load_settings()

    def _init_ui(self):
        """Initialize the enhanced UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Set better size constraints for the main widget
        self.setMinimumSize(800, 600)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Main splitter for flexible layout
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.main_splitter)

        # Left panel (sidebar)
        self.left_panel = self._create_left_panel()
        self.main_splitter.addWidget(self.left_panel)

        # Right panel (main content)
        self.right_panel = self._create_right_panel()
        self.main_splitter.addWidget(self.right_panel)

        # Set splitter proportions (sidebar: 30%, main: 70%)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([300, 700])

    def _create_left_panel(self) -> QWidget:
        """Create left panel with controls"""
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Recording controls
        self.recording_controls = RecordingControlsWidget()
        left_layout.addWidget(self.recording_controls)

        # Model selectors
        self.model_selectors = ModelSelectorsWidget()
        left_layout.addWidget(self.model_selectors)

        # Dictation controls now integrated into ModelSelectorsWidget

        left_layout.addStretch()

        return left_panel

    def _create_right_panel(self) -> QWidget:
        """Create right panel with conversation"""
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Transcription panel (top)
        self.transcription_panel = EnhancedTranscriptionPanel()
        right_layout.addWidget(self.transcription_panel)

        # Response panel (bottom) - takes remaining space
        self.response_panel = EnhancedResponsePanel()
        self.response_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.response_panel)

        return right_panel

    def _connect_signals(self):
        """Connect all signals"""
        # Recording controls
        self.recording_controls.start_listening_requested.connect(self._on_start_listening)
        self.recording_controls.stop_listening_requested.connect(self._on_stop_listening)
        self.recording_controls.manual_activation_requested.connect(self._on_manual_activation)

        # Transcription panel
        self.transcription_panel.custom_text_toggled.connect(self._on_custom_text_toggled)
        self.transcription_panel.play_text_requested.connect(self._on_play_text_requested)
        self.transcription_panel.transcription_updated.connect(self._on_transcription_updated)

        # Response panel
        self.response_panel.response_updated.connect(self._on_response_updated)
        self.response_panel.conversation_cleared.connect(self._on_conversation_cleared)

        # Model selectors
        self.model_selectors.asr_model_changed.connect(self._on_asr_model_changed)
        self.model_selectors.tts_model_changed.connect(self._on_tts_model_changed)

        # Mode controls
        self.model_selectors.dictation_mode_changed.connect(self._on_mode_toggled)

        # Voice processor callbacks
        if self.voice_processor:
            self.voice_processor.transcription_received.connect(self._on_transcription_received)

    def _load_settings(self):
        """Load settings from settings manager"""
        try:
            # Load model selections
            asr_model = self.settings_manager.get("asr_model", "canary")
            tts_model = self.settings_manager.get("tts_model", "kittentts")
            
            self.model_selectors.set_asr_model(asr_model)
            self.model_selectors.set_tts_model(tts_model)

            # Load recording settings
            sensitivity = self.settings_manager.get("sensitivity", "Medium")
            auto_vad = self.settings_manager.get("auto_vad_enabled", False)
            
            self.recording_controls.set_sensitivity(sensitivity)
            self.recording_controls.set_auto_vad_enabled(auto_vad)

            # Load response settings
            verbosity = self.settings_manager.get("verbosity", "balanced")
            translation_enabled = self.settings_manager.get("translation_enabled", False)
            
            self.response_panel.set_verbosity(verbosity)
            self.response_panel.set_translation_enabled(translation_enabled)

            # Load mode settings
            is_dictation = self.settings_manager.get("is_dictation_mode", False)
            self.model_selectors.set_dictation_mode(is_dictation)

        except Exception as e:
            logger.error(f"Failed to load settings: {e}")

    def _save_settings(self):
        """Save current settings"""
        try:
            # Save model selections
            self.settings_manager.set("asr_model", self.model_selectors.get_asr_model())
            self.settings_manager.set("tts_model", self.model_selectors.get_tts_model())

            # Save recording settings
            self.settings_manager.set("sensitivity", self.recording_controls.get_sensitivity())
            self.settings_manager.set("auto_vad_enabled", self.recording_controls.is_auto_vad_enabled())

            # Save response settings
            self.settings_manager.set("verbosity", self.response_panel.get_verbosity())
            self.settings_manager.set("translation_enabled", self.response_panel.is_translation_enabled())

            # Save mode settings
            self.settings_manager.set("is_dictation_mode", self.model_selectors.is_dictation_mode())

        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    # Signal handlers
    def _on_start_listening(self):
        """Handle start listening request"""
        logger.info("Start listening requested")
        
        if self.voice_processor:
            try:
                self.voice_processor.start_listening()
                self.recording_controls.set_listening_state(True)
                self.start_listening_requested.emit()
            except Exception as e:
                logger.error(f"Failed to start listening: {e}")
                InfoBar.error(
                    "Recording Error",
                    f"Failed to start recording: {e}",
                    parent=self,
                    duration=3000,
                )

    def _on_stop_listening(self):
        """Handle stop listening request"""
        logger.info("Stop listening requested")
        
        if self.voice_processor:
            try:
                self.voice_processor.stop_listening()
                self.recording_controls.set_listening_state(False)
                self.stop_listening_requested.emit()
            except Exception as e:
                logger.error(f"Failed to stop listening: {e}")

    def _on_manual_activation(self):
        """Handle manual activation request"""
        logger.info("Manual activation requested")
        self.manual_activation_requested.emit()

    def _on_custom_text_toggled(self, enabled: bool):
        """Handle custom text mode toggle"""
        logger.info(f"Custom text mode {'enabled' if enabled else 'disabled'}")

    def _on_play_text_requested(self, text: str):
        """Handle play text request"""
        logger.info(f"Play text requested: {text[:50]}...")
        
        # Determine text type and handle accordingly
        text_type = self.transcription_panel.get_text_type()
        
        if text_type == "url":
            self._handle_url_playback(text)
        elif text_type == "search":
            self._handle_search_playback(text)
        else:
            self._handle_text_playback(text)

    def _handle_text_playback(self, text: str):
        """Handle plain text playback"""
        if self.tts_manager:
            try:
                self.tts_manager.speak_text(text)
            except Exception as e:
                logger.error(f"Failed to play text: {e}")
                InfoBar.error(
                    "Playback Error",
                    f"Failed to play text: {e}",
                    parent=self,
                    duration=3000,
                )

    def _handle_url_playback(self, url: str):
        """Handle URL playback"""
        # This would integrate with URL processor
        logger.info(f"URL playback requested: {url}")
        
        # For now, just treat as text
        self._handle_text_playback(f"URL content for: {url}")

    def _handle_search_playback(self, query: str):
        """Handle search query playback"""
        # This would integrate with web search
        logger.info(f"Search playback requested: {query}")
        
        # For now, just treat as text
        self._handle_text_playback(f"Search results for: {query}")

    def _on_transcription_updated(self, text: str):
        """Handle transcription update"""
        # Add to conversation context
        if text.strip():
            self.conversation_context.add_message("user", text)
            
            # Detect topic changes
            self.advanced_context.detect_topic_change(text)
            
            # Process with LLM if in Voice AI mode
            if not self.model_selectors.is_dictation_mode():
                self._process_with_llm(text)

    def _on_transcription_received(self, text: str):
        """Handle transcription from voice processor"""
        # Update transcription panel
        self.transcription_panel.append_transcription(text)
        
        # Add to conversation context
        if text.strip():
            self.conversation_context.add_message("user", text)
            
            # Detect topic changes
            self.advanced_context.detect_topic_change(text)
            
            # Process with LLM if in Voice AI mode
            if not self.model_selectors.is_dictation_mode():
                self._process_with_llm(text)

    def _process_with_llm(self, user_text: str):
        """Process user text with LLM"""
        if not self.llm_manager:
            logger.warning("No LLM manager available")
            return

        try:
            # Get conversation context
            context_messages = self.conversation_context.get_context_for_llm()
            
            # Get response settings
            verbosity = self.response_panel.get_verbosity()
            translation_enabled = self.response_panel.is_translation_enabled()
            target_language = self.response_panel.get_target_language()
            
            # Generate response
            response = self.llm_manager.generate_response(
                user_text,
                context_messages=context_messages,
                verbosity=verbosity,
                translation_enabled=translation_enabled,
                target_language=target_language
            )
            
            # Add to response panel
            self.response_panel.add_message("assistant", response)
            
            # Add to conversation context
            self.conversation_context.add_message("assistant", response)
            
            # Speak response if TTS is available
            if self.tts_manager:
                self.tts_manager.speak_text(response)

        except Exception as e:
            logger.error(f"Failed to process with LLM: {e}")
            error_msg = f"Sorry, I encountered an error: {str(e)}"
            self.response_panel.add_message("assistant", error_msg)

    def _on_response_updated(self, text: str):
        """Handle response update"""
        logger.debug(f"Response updated: {text[:50]}...")

    def _on_conversation_cleared(self):
        """Handle conversation cleared"""
        logger.info("Conversation cleared")
        
        # Clear conversation context
        self.conversation_context.clear_conversation()
        
        # Clear transcription
        self.transcription_panel.clear_transcription()

    def _on_asr_model_changed(self, model_id: str):
        """Handle ASR model change"""
        logger.info(f"ASR model changed to: {model_id}")
        self.settings_manager.set("asr_model", model_id)

    def _on_tts_model_changed(self, model_id: str):
        """Handle TTS model change"""
        logger.info(f"TTS model changed to: {model_id}")
        self.settings_manager.set("tts_model", model_id)

    def _on_mode_toggled(self, is_dictation_mode: bool):
        """Handle mode toggle"""
        logger.info(f"Mode changed to: {'Dictation' if is_dictation_mode else 'Voice AI'}")
        self.settings_manager.set("is_dictation_mode", is_dictation_mode)

    # Public API methods
    def set_current_session(self, session_id: str):
        """Set current session"""
        self.current_session_id = session_id
        
        # Load conversation history for this session
        session = self.session_manager.get_session(session_id)
        if session and session.messages:
            # Convert session messages to conversation context
            self.conversation_context.clear_conversation()
            
            for msg in session.messages:
                role = "user" if msg.get("role") == "user" else "assistant"
                content = msg.get("content", "")
                if content:
                    self.conversation_context.add_message(role, content)
            
            # Update response panel
            self.response_panel.set_conversation_history(session.messages)

    def save_current_session(self):
        """Save current conversation to session"""
        if not self.current_session_id:
            return
        
        # Get conversation history
        history = self.response_panel.get_conversation_history()
        
        # Update session
        session = self.session_manager.get_session(self.current_session_id)
        if session:
            session.messages = history
            self.session_manager.save_sessions()

    def get_conversation_stats(self) -> dict:
        """Get conversation statistics"""
        return self.conversation_context.get_conversation_stats()

    def enable_smooth_scroll(self, enabled: bool = True):
        """Enable smooth scrolling for all panels"""
        self.transcription_panel.enable_smooth_scroll(enabled)
        self.response_panel.enable_smooth_scroll(enabled)

    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        
        # Adjust splitter proportions on resize
        if hasattr(self, 'main_splitter'):
            width = self.width()
            if width < 1000:
                # Compact mode - smaller sidebar
                self.main_splitter.setSizes([250, width - 250])
            else:
                # Normal mode
                self.main_splitter.setSizes([300, width - 300])

    def closeEvent(self, event):
        """Handle close event"""
        self._save_settings()
        self.save_current_session()
        super().closeEvent(event)