"""
Chat Sidebar Widget
Sidebar with chat sessions and new chat button
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QComboBox,
    QLineEdit,
    QMenu,
    QInputDialog,
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QIcon, QAction, QColor

from qfluentwidgets import (
    PushButton,
    ComboBox,
    LineEdit,
    CardWidget,
    BodyLabel,
    PrimaryPushButton,
    IconWidget,
    FluentIcon,
    TransparentToolButton,
)


class ChatSidebar(QWidget):
    """Sidebar widget for chat session management"""

    # Signals
    session_selected = Signal(str)  # session_id
    new_chat_requested = Signal()
    session_renamed = Signal(str, str)  # session_id, new_name
    session_deleted = Signal(str)  # session_id
    sidebar_collapsed = Signal(bool)  # is_collapsed

    def __init__(self, session_manager, parent=None):
        super().__init__(parent)
        self.session_manager = session_manager
        self.is_collapsed = False
        self.init_ui()
        self.refresh_session_list()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header with title, collapse button, and new chat button
        header_layout = QHBoxLayout()

        title_label = BodyLabel("Chats")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Collapse button
        self.collapse_btn = TransparentToolButton(FluentIcon.MENU, self)
        self.collapse_btn.setToolTip("Collapse sidebar")
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.collapse_btn)

        # New chat button
        self.new_chat_btn = TransparentToolButton(FluentIcon.ADD, self)
        self.new_chat_btn.setToolTip("New Chat")
        self.new_chat_btn.clicked.connect(self._on_new_chat)
        header_layout.addWidget(self.new_chat_btn)

        layout.addLayout(header_layout)

        # Session list
        self.session_list = QListWidget()
        self.session_list.setSpacing(2)
        self.session_list.itemClicked.connect(self._on_session_clicked)
        self.session_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.session_list.customContextMenuRequested.connect(self._on_context_menu)

        layout.addWidget(self.session_list)

        # Set minimum width
        self.setMinimumWidth(220)
        self.setMaximumWidth(300)

    def _on_collapse_clicked(self):
        """Handle collapse button click"""
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.collapse_btn.setIcon(FluentIcon.MENU)
            self.collapse_btn.setToolTip("Expand Sidebar")
            self.setMaximumWidth(40)
            self.session_list.hide()
            self.setMinimumWidth(40)
        else:
            self.collapse_btn.setIcon(FluentIcon.ARROW_LEFT)
            self.collapse_btn.setToolTip("Collapse Sidebar")
            self.setMaximumWidth(300)
            self.session_list.show()
            self.setMinimumWidth(220)

        # Emit signal for parent to handle layout
        self.sidebar_collapsed.emit(self.is_collapsed)

    def refresh_session_list(self):
        """Refresh the session list"""
        self.session_list.clear()

        sessions = self.session_manager.get_all_sessions()
        current_id = self.session_manager.current_session_id

        for session in sessions:
            item = QListWidgetItem(session.name)
            item.setData(Qt.ItemDataRole.UserRole, session.session_id)

            # Highlight current session
            if session.session_id == current_id:
                item.setSelected(True)
                item.setBackground(QColor("#21262d"))

            # Add timestamp as tooltip
            from datetime import datetime

            try:
                dt = datetime.fromisoformat(session.updated_at)
                tooltip = dt.strftime("%b %d, %Y at %H:%M")
            except:
                tooltip = session.updated_at

            item.setToolTip(f"Last updated: {tooltip}")

            self.session_list.addItem(item)

    def _on_new_chat(self):
        """Handle new chat button click"""
        self.new_chat_requested.emit()

    def _on_session_clicked(self, item):
        """Handle session selection"""
        session_id = item.data(Qt.ItemDataRole.UserRole)
        if session_id:
            self.session_selected.emit(session_id)

    def _on_context_menu(self, position):
        """Show context menu for session"""
        item = self.session_list.itemAt(position)
        if not item:
            return

        session_id = item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)

        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(lambda: self._rename_session(session_id))
        menu.addAction(rename_action)

        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self._delete_session(session_id))
        menu.addAction(delete_action)

        menu.exec(self.session_list.viewport().mapToGlobal(position))

    def _rename_session(self, session_id):
        """Rename a session"""
        session = self.session_manager.sessions.get(session_id)
        if not session:
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Chat",
            "Enter new name:",
            QLineEdit.EchoMode.Normal,
            session.name,
        )

        if ok and new_name.strip():
            self.session_manager.rename_session(session_id, new_name.strip())
            self.session_renamed.emit(session_id, new_name.strip())
            self.refresh_session_list()

    def _delete_session(self, session_id):
        """Delete a session"""
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Delete Chat",
            "Are you sure you want to delete this chat? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.session_deleted.emit(session_id)
            self.session_manager.delete_session(session_id)
            self.refresh_session_list()

    def set_current_session(self, session_id):
        """Set current session in sidebar"""
        for i in range(self.session_list.count()):
            item = self.session_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == session_id:
                self.session_list.setCurrentItem(item)
                break

    def toggle_collapse(self):
        """Toggle sidebar collapse state"""
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.collapse_btn.setIcon(FluentIcon.MENU)
            self.collapse_btn.setToolTip("Expand Sidebar")
            self.setMaximumWidth(40)
            self.session_list.hide()
            self.setMinimumWidth(40)
        else:
            self.collapse_btn.setIcon(FluentIcon.ARROW_LEFT)
            self.collapse_btn.setToolTip("Collapse Sidebar")
            self.setMaximumWidth(300)
            self.session_list.show()
            self.setMinimumWidth(220)
        
        # Emit signal for parent to handle layout
        self.sidebar_collapsed.emit(self.is_collapsed)