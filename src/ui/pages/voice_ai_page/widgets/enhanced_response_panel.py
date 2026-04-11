"""
Enhanced Response Panel with Event-Based Organization

Features:
- Events grouped by timestamp (each dictation = one event)
- Visual separation between events
- Smooth scrolling with auto-scroll controls
- Conversation context visualization
- Modern chat interface similar to ChatGPT/Perplexity
"""

import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QComboBox, QCheckBox, QSizePolicy,
    QTextEdit
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QPalette, QColor

from qfluentwidgets import (
    BodyLabel, PushButton, ComboBox, SwitchButton, CardWidget,
    TextEdit, ScrollArea, InfoBar, FluentIcon
)

from src.markdown_display import ScrollableMarkdownDisplay as MarkdownDisplay

logger = logging.getLogger(__name__)


class ResponseEventWidget(QWidget):
    """Individual response event widget with timestamp header"""
    
    def __init__(self, event_id: str, timestamp: str, parent=None):
        super().__init__(parent)
        self.event_id = event_id
        self.timestamp = timestamp
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the event widget UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Event header with timestamp
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #21262d;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 12, 6)
        
        # Clock icon and timestamp
        time_label = QLabel(f"🕐 {self.timestamp}")
        time_label.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: bold;")
        header_layout.addWidget(time_label)
        header_layout.addStretch()
        
        layout.addWidget(header)
        
        # Content display (using MarkdownDisplay for rich text)
        self.content_display = MarkdownDisplay()
        self.content_display.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        layout.addWidget(self.content_display)
    
    def append_text(self, text: str):
        """Append text to this event's content"""
        self.content_display.append_markdown(text)
    
    def set_text(self, text: str):
        """Set the content text"""
        self.content_display.setMarkdown(text)
    
    def get_content(self) -> str:
        """Get the content text"""
        # Get text from the markdown display
        return self.content_display.toPlainText()
    
    def clear(self):
        """Clear the content"""
        self.content_display.setMarkdown("")


class EnhancedResponsePanel(QWidget):
    """
    Enhanced response panel with event-based organization
    
    Each dictation/voice session creates a new event with timestamp.
    Events are displayed in a scrollable list with visual separation.
    """

    # Signals
    response_updated = Signal(str)
    auto_scroll_toggled = Signal(bool)
    conversation_cleared = Signal()
    verbosity_changed = Signal(str)  # verbosity level
    translation_toggled = Signal(bool)
    target_language_changed = Signal(str)  # lang_code

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EnhancedResponsePanel")
        
        # Event tracking
        self.events = {}  # event_id -> ResponseEventWidget
        self.current_event_id = None
        
        # Scroll state
        self.auto_scroll_enabled = True
        self.smooth_scroll_enabled = True
        
        self._init_ui()

    def _init_ui(self):
        """Initialize the enhanced UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with controls - Updated title to TTS Output
        header_widget = self._create_header()
        layout.addWidget(header_widget)

        # Scroll area for events
        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Container for event widgets
        self.events_container = QWidget()
        self.events_layout = QVBoxLayout(self.events_container)
        self.events_layout.setContentsMargins(8, 8, 8, 8)
        self.events_layout.setSpacing(12)
        self.events_layout.addStretch()
        
        self.scroll_area.setWidget(self.events_container)
        layout.addWidget(self.scroll_area)

        # Footer with scroll controls
        footer_widget = self._create_footer()
        layout.addWidget(footer_widget)

        # Set minimum size with better constraints
        self.setMinimumSize(400, 250)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _format_timestamp(self, dt: datetime = None) -> str:
        """Format timestamp for display"""
        if dt is None:
            dt = datetime.now()
        
        now = datetime.now()
        today = now.date()
        event_date = dt.date()
        
        if event_date == today:
            return f"Today at {dt.strftime('%H:%M')}"
        elif event_date == today.replace(day=today.day - 1):
            return f"Yesterday at {dt.strftime('%H:%M')}"
        else:
            return dt.strftime("%b %d, %Y at %H:%M")

    def _create_header(self) -> QWidget:
        """Create header with response controls"""
        header = CardWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        # Title - Updated to TTS Output
        title = BodyLabel("TTS Output (Processed Result)")
        title.setStyleSheet("font-weight: bold; font-size: 16px; color: #e6edf3;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Verbosity selector
        header_layout.addWidget(BodyLabel("Style:"))
        self.verbosity_combo = ComboBox()
        self.verbosity_combo.addItems(["Concise", "Balanced", "Detailed"])
        self.verbosity_combo.setCurrentText("Balanced")
        self.verbosity_combo.setFixedWidth(100)
        self.verbosity_combo.currentTextChanged.connect(lambda text: self.verbosity_changed.emit(text.lower()))
        header_layout.addWidget(self.verbosity_combo)

        # Translation toggle
        self.translation_toggle = SwitchButton()
        self.translation_toggle.setText("Translate")
        self.translation_toggle.setChecked(False)
        self.translation_toggle.checkedChanged.connect(self.translation_toggled.emit)
        header_layout.addWidget(self.translation_toggle)

        # Clear conversation button
        self.clear_btn = PushButton("Clear Chat")
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self.clear_btn.setStyleSheet("""
            PushButton {
                background-color: #da3633;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
            }
            PushButton:hover { background-color: #f85149; }
        """)
        header_layout.addWidget(self.clear_btn)

        return header

    def _create_footer(self) -> QWidget:
        """Create footer with scroll controls"""
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 8, 16, 8)

        # Auto-scroll toggle
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.toggled.connect(self._on_auto_scroll_toggled)
        self.auto_scroll_check.setStyleSheet("color: #8b949e;")
        footer_layout.addWidget(self.auto_scroll_check)

        footer_layout.addStretch()

        # Scroll controls
        self.scroll_to_top_btn = PushButton("↑ Top")
        self.scroll_to_top_btn.clicked.connect(self.scroll_to_top)
        self.scroll_to_top_btn.setFixedWidth(60)
        footer_layout.addWidget(self.scroll_to_top_btn)

        self.scroll_to_bottom_btn = PushButton("↓ Bottom")
        self.scroll_to_bottom_btn.clicked.connect(self.scroll_to_bottom)
        self.scroll_to_bottom_btn.setFixedWidth(60)
        footer_layout.addWidget(self.scroll_to_bottom_btn)

        return footer

    def create_event(self, event_id: str = None, timestamp: str = None) -> str:
        """
        Create a new response event with timestamp
        
        Args:
            event_id: Optional event ID. If None, generates one from timestamp.
            timestamp: Optional timestamp string. If None, generates from current time.
            
        Returns:
            The event_id of the created event
        """
        if event_id is None:
            event_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # If there's a current event, we're done with it
        self.current_event_id = event_id
        
        # Use provided timestamp or generate one
        if timestamp is None:
            timestamp = self._format_timestamp()
        
        # Create event widget
        event_widget = ResponseEventWidget(event_id, timestamp)
        
        # Insert before the stretch
        self.events_layout.insertWidget(self.events_layout.count() - 1, event_widget)
        self.events[event_id] = event_widget
        
        # Auto-scroll to bottom
        if self.auto_scroll_enabled:
            QTimer.singleShot(50, self.scroll_to_bottom)
        
        return event_id

    def get_current_event_id(self) -> str:
        """Get the current event ID"""
        return self.current_event_id

    def add_message(self, role: str, content: str, timestamp: str = None):
        """
        Add a message to the conversation (legacy compatibility)
        
        Args:
            role: Message role ("user", "assistant")
            content: Message content
            timestamp: Optional timestamp
        """
        # For compatibility, just append to current event
        self.append_response(content)

    def append_response(self, text: str, event_id: str = None):
        """
        Append text to the response display
        
        Args:
            text: Text to append
            event_id: Optional event ID. If None, uses current event or creates new one.
        """
        # Use specified event_id or current event or create new
        target_event_id = event_id or self.current_event_id
        
        if target_event_id is None:
            # No current event, create one
            target_event_id = self.create_event()
        
        event = self.events.get(target_event_id)
        if event:
            event.append_text(text)
            
            # Auto-scroll to bottom
            if self.auto_scroll_enabled:
                QTimer.singleShot(50, self.scroll_to_bottom)

            self.response_updated.emit(text)

    def set_response(self, text: str, event_id: str = None):
        """
        Set the response text (replaces current response)
        
        Args:
            text: Text to set
            event_id: Optional event ID. If None, uses current event.
        """
        target_event_id = event_id or self.current_event_id
        
        if target_event_id is None:
            target_event_id = self.create_event()
        
        event = self.events.get(target_event_id)
        if event:
            event.set_text(text)

    def get_response_text(self, event_id: str = None) -> str:
        """Get response text for a specific event or current event"""
        if event_id is None:
            event_id = self.current_event_id
            
        if event_id and event_id in self.events:
            return self.events[event_id].get_content()
        return ""

    def get_all_text(self) -> str:
        """Get all response text from all events"""
        texts = []
        for event_id, event in self.events.items():
            content = event.get_content()
            if content:
                texts.append(f"[{event.timestamp}]\n{content}")
        return "\n\n".join(texts)

    def clear_response(self):
        """Clear all response events"""
        for event in list(self.events.values()):
            self.events_layout.removeWidget(event)
            event.deleteLater()
        self.events.clear()
        self.current_event_id = None
        self.conversation_cleared.emit()

    def clear_event(self, event_id: str):
        """Clear a specific event"""
        if event_id in self.events:
            event = self.events[event_id]
            self.events_layout.removeWidget(event)
            event.deleteLater()
            del self.events[event_id]
            
            if self.current_event_id == event_id:
                self.current_event_id = None

    def scroll_to_bottom(self):
        """Scroll to bottom of conversation"""
        if self.smooth_scroll_enabled:
            self._smooth_scroll_to_bottom()
        else:
            scrollbar = self.scroll_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def scroll_to_top(self):
        """Scroll to top of conversation"""
        if self.smooth_scroll_enabled:
            self._smooth_scroll_to_top()
        else:
            self.scroll_area.verticalScrollBar().setValue(0)

    def _smooth_scroll_to_bottom(self):
        """Smooth scroll to bottom with animation"""
        scrollbar = self.scroll_area.verticalScrollBar()
        target_value = scrollbar.maximum()
        
        animation = QPropertyAnimation(scrollbar, b"value")
        animation.setDuration(300)
        animation.setStartValue(scrollbar.value())
        animation.setEndValue(target_value)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start()

    def _smooth_scroll_to_top(self):
        """Smooth scroll to top with animation"""
        scrollbar = self.scroll_area.verticalScrollBar()
        
        animation = QPropertyAnimation(scrollbar, b"value")
        animation.setDuration(300)
        animation.setStartValue(scrollbar.value())
        animation.setEndValue(0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start()

    def _on_auto_scroll_toggled(self, checked: bool):
        """Handle auto-scroll toggle"""
        self.auto_scroll_enabled = checked
        self.auto_scroll_toggled.emit(checked)

    def _on_clear_clicked(self):
        """Handle clear conversation click"""
        self.clear_response()

    def get_event_count(self) -> int:
        """Get number of events"""
        return len(self.events)

    def get_current_event(self):
        """Get current event widget"""
        if self.current_event_id and self.current_event_id in self.events:
            return self.events[self.current_event_id]
        return None

    def get_conversation_history(self) -> list:
        """Get conversation history as list of dicts (legacy compatibility)"""
        history = []
        for event_id, event in self.events.items():
            history.append({
                "role": "assistant",
                "content": event.get_content(),
                "timestamp": event.timestamp
            })
        return history

    def set_conversation_history(self, history: list):
        """Set conversation history from list of dicts (legacy compatibility)"""
        self.clear_response()
        
        for msg_data in history:
            event_id = self.create_event()
            event = self.events.get(event_id)
            if event:
                event.set_text(msg_data.get("content", ""))

    # Property accessors
    def get_verbosity(self) -> str:
        """Get current verbosity setting"""
        return self.verbosity_combo.currentText().lower()

    def set_verbosity(self, verbosity: str):
        """Set verbosity setting"""
        verbosity = verbosity.capitalize()
        if verbosity in ["Concise", "Balanced", "Detailed"]:
            self.verbosity_combo.setCurrentText(verbosity)

    def is_translation_enabled(self) -> bool:
        """Check if translation is enabled"""
        return self.translation_toggle.isChecked()

    def set_translation_enabled(self, enabled: bool):
        """Set translation enabled state"""
        self.translation_toggle.setChecked(enabled)

    def get_target_language(self) -> str:
        """Get target language (placeholder - would connect to language selector)"""
        return "en"  # Default to English

    def set_target_language(self, lang_code: str):
        """Set target language (placeholder)"""
        pass  # Would connect to language selector

    def enable_smooth_scroll(self, enabled: bool = True):
        """Enable or disable smooth scrolling"""
        self.smooth_scroll_enabled = enabled
