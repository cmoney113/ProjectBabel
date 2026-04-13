"""
Enhanced Transcription Panel with Event-Based Organization

Features:
- Events grouped by timestamp (each dictation = one event)
- Visual separation between events
- Improved scroll behavior with auto-scroll controls
- Better minimum size handling
- Modern chat-like interface for transcription
"""

import re
import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QScrollBar,
    QSizePolicy, QFrame, QLabel
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QTextCursor, QFont

from qfluentwidgets import (
    BodyLabel, SwitchButton, PushButton, CardWidget, InfoBar,
    ScrollArea, FluentIcon
)

logger = logging.getLogger(__name__)


class TranscriptionEventWidget(QWidget):
    """Individual transcription event widget with timestamp header"""
    
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
        
        # Content text edit
        self.content_edit = QTextEdit()
        self.content_edit.setReadOnly(True)
        self.content_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1a1f26;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
                font-size: 14px;
                line-height: 1.5;
                selection-background-color: #238636;
                selection-color: #ffffff;
            }
        """)
        layout.addWidget(self.content_edit)
    
    def append_text(self, text: str):
        """Append text to this event's content"""
        current = self.content_edit.toPlainText()
        if current and not current.endswith("\n"):
            self.content_edit.append("")
        self.content_edit.append(text)
    
    def get_content(self) -> str:
        """Get the content text"""
        return self.content_edit.toPlainText()
    
    def clear(self):
        """Clear the content"""
        self.content_edit.clear()


class EnhancedTranscriptionPanel(QWidget):
    """
    Enhanced transcription panel with event-based organization
    
    Each dictation/voice session creates a new event with timestamp.
    Events are displayed in a scrollable list with visual separation.
    """

    # Signals
    custom_text_toggled = Signal(bool)
    play_text_requested = Signal(str)
    transcription_updated = Signal(str)
    tools_toggled = Signal(bool)  # AI tools enabled/disabled

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EnhancedTranscriptionPanel")
        
        # Scroll state
        self.auto_scroll_enabled = True
        self.smooth_scroll_enabled = True
        
        # Event tracking
        self.events = {}  # event_id -> TranscriptionEventWidget
        self.current_event_id = None
        
        self._init_ui()

    def _init_ui(self):
        """Initialize the enhanced UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Card container
        self.card = CardWidget()
        card_layout = QVBoxLayout(self.card)

        # Title - Updated to ASR Output
        title = BodyLabel("ASR Output (Raw Transcription)")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #e6edf3;")
        card_layout.addWidget(title)

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
        card_layout.addWidget(self.scroll_area)

        # Set minimum height for the scroll area
        self.scroll_area.setMinimumHeight(120)
        self.scroll_area.setMaximumHeight(200)

        # Custom text toggle + play button
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(BodyLabel("📝 Custom Text Mode:"))

        self.custom_text_toggle = SwitchButton()
        self.custom_text_toggle.setChecked(False)
        self.custom_text_toggle.checkedChanged.connect(self._on_custom_text_toggled)
        self.custom_text_toggle.setToolTip(
            "Enable to type/paste text, URLs, or search queries. URLs are fetched & read. Searches show results to select."
        )
        custom_layout.addWidget(self.custom_text_toggle)

        self.play_text_btn = PushButton("▶ Play")
        self.play_text_btn.setToolTip(
            "Play the entered text via TTS. Works with plain text, URLs (fetches article), or search queries."
        )
        self.play_text_btn.clicked.connect(self._on_play_text_clicked)
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
        custom_layout.addWidget(self.play_text_btn)
        # Tools toggle - enables TermPipe tools for the AI
        custom_layout.addSpacing(20)
        custom_layout.addWidget(BodyLabel("🔧 AI Tools:"))

        self.tools_toggle = SwitchButton()
        self.tools_toggle.setChecked(True)  # Default ON
        self.tools_toggle.setToolTip(
            "Enable AI tools: file operations, web search, shell commands, etc. The AI can use these to help answer your requests."
        )
        self.tools_toggle.checkedChanged.connect(self._on_tools_toggled)
        custom_layout.addWidget(self.tools_toggle)

        custom_layout.addStretch()
        card_layout.addLayout(custom_layout)

        layout.addWidget(self.card)

        # Set better minimum size for the panel
        self.setMinimumSize(400, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

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

    def create_event(self, event_id: str = None) -> str:
        """
        Create a new transcription event with timestamp
        
        Args:
            event_id: Optional event ID. If None, generates one from timestamp.
            
        Returns:
            The event_id of the created event
        """
        if event_id is None:
            event_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # If there's a current event, we're done with it
        self.current_event_id = event_id
        
        # Create timestamp
        timestamp = self._format_timestamp()
        
        # Create event widget
        event_widget = TranscriptionEventWidget(event_id, timestamp)
        
        # Insert before the stretch
        self.events_layout.insertWidget(self.events_layout.count() - 1, event_widget)
        self.events[event_id] = event_widget
        
        # Auto-scroll to bottom
        if self.auto_scroll_enabled:
            QTimer.singleShot(50, self._scroll_to_bottom)
        
        return event_id

    def get_current_event_id(self) -> str:
        """Get the current event ID"""
        return self.current_event_id

    # Signal handlers
    def _on_custom_text_toggled(self, checked: bool):
        """Handle custom text mode toggle"""
        if checked:
            # Create a new event for custom text
            self.create_event("custom_text")
            event = self.events.get(self.current_event_id)
            if event:
                event.content_edit.setReadOnly(False)
                event.content_edit.setPlaceholderText(
                    "Enter custom text here and click Play..."
                )
                event.content_edit.setFocus()
            
            self.play_text_btn.setVisible(True)
            self.play_text_btn.setEnabled(True)
        else:
            # Restore read-only state
            event = self.events.get(self.current_event_id)
            if event:
                event.content_edit.setReadOnly(True)
                event.content_edit.setPlaceholderText("")
            
            self.play_text_btn.setVisible(False)
            self.play_text_btn.setEnabled(False)

        self.custom_text_toggled.emit(checked)

    def _on_play_text_clicked(self):
        """Handle play button click"""
        event = self.events.get(self.current_event_id)
        if not event:
            return
            
        text = event.get_content().strip()
        if not text:
            InfoBar.warning(
                "No Text",
                "Please enter text to play",
                parent=self,
                duration=2000,
            )
            return

        self.play_text_requested.emit(text)

    def _on_tools_toggled(self, checked: bool):
        """Handle AI tools toggle"""
        if checked:
            InfoBar.success(
                "AI Tools",
                "Tools enabled: file ops, web search, shell commands",
                parent=self,
                duration=2000,
            )
        else:
            InfoBar.info(
                "AI Tools",
                "Tools disabled - basic chat only",
                parent=self,
                duration=2000,
            )
        self.tools_toggled.emit(checked)

    # Public API
    def append_transcription(self, text: str, event_id: str = None):
        """
        Append text to transcription display
        
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
                QTimer.singleShot(50, self._scroll_to_bottom)

            self.transcription_updated.emit(text)

    def _scroll_to_bottom(self):
        """Scroll to bottom with smooth animation"""
        if self.smooth_scroll_enabled:
            self._smooth_scroll_to_bottom()
        else:
            scrollbar = self.scroll_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _smooth_scroll_to_bottom(self):
        """Smooth scroll to bottom with animation"""
        scrollbar = self.scroll_area.verticalScrollBar()
        target_value = scrollbar.maximum()
        
        # Only animate if we're not already at the bottom
        if abs(scrollbar.value() - target_value) > 10:
            animation = QPropertyAnimation(scrollbar, b"value")
            animation.setDuration(200)
            animation.setStartValue(scrollbar.value())
            animation.setEndValue(target_value)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.start()
        else:
            # Already near bottom, just jump there
            scrollbar.setValue(target_value)

    def get_transcription_text(self, event_id: str = None) -> str:
        """Get transcription text for a specific event or current event"""
        if event_id is None:
            event_id = self.current_event_id
            
        if event_id and event_id in self.events:
            return self.events[event_id].get_content()
        return ""

    def get_all_text(self) -> str:
        """Get all transcription text from all events"""
        texts = []
        for event_id, event in self.events.items():
            content = event.get_content()
            if content:
                texts.append(f"[{event.timestamp}]\n{content}")
        return "\n\n".join(texts)

    def clear_transcription(self):
        """Clear all transcription events"""
        for event in list(self.events.values()):
            self.events_layout.removeWidget(event)
            event.deleteLater()
        self.events.clear()
        self.current_event_id = None

    def clear_event(self, event_id: str):
        """Clear a specific event"""
        if event_id in self.events:
            event = self.events[event_id]
            self.events_layout.removeWidget(event)
            event.deleteLater()
            del self.events[event_id]
            
            if self.current_event_id == event_id:
                self.current_event_id = None

    def set_custom_text_mode(self, enabled: bool):
        """Set custom text mode enabled state"""
        self.custom_text_toggle.setChecked(enabled)

    def is_custom_text_enabled(self) -> bool:
        """Check if custom text mode is enabled"""
        return self.custom_text_toggle.isChecked()

    def is_tools_enabled(self) -> bool:
        """Check if AI tools are enabled"""
        return self.tools_toggle.isChecked()

    def set_tools_enabled(self, enabled: bool):
        """Set AI tools enabled state"""
        self.tools_toggle.setChecked(enabled)

    def enable_auto_scroll(self, enabled: bool = True):
        """Enable or disable auto-scroll"""
        self.auto_scroll_enabled = enabled

    def enable_smooth_scroll(self, enabled: bool = True):
        """Enable or disable smooth scrolling"""
        self.smooth_scroll_enabled = enabled

    def scroll_to_bottom(self):
        """Manually scroll to bottom"""
        self._scroll_to_bottom()

    def scroll_to_top(self):
        """Scroll to top"""
        scrollbar = self.scroll_area.verticalScrollBar()
        
        if self.smooth_scroll_enabled:
            animation = QPropertyAnimation(scrollbar, b"value")
            animation.setDuration(200)
            animation.setStartValue(scrollbar.value())
            animation.setEndValue(0)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.start()
        else:
            scrollbar.setValue(0)

    def get_event_count(self) -> int:
        """Get number of events"""
        return len(self.events)

    def get_current_event(self):
        """Get current event widget"""
        if self.current_event_id and self.current_event_id in self.events:
            return self.events[self.current_event_id]
        return None
