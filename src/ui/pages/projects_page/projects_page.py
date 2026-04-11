"""
Projects Page - Perplexity-like Spaces feature
A place where users can create projects with context (files, URLs, text, images)
and chat with AI that has full access to that context.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from PySide6.QtCore import Qt, Signal, Slot, QThread, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QStackedWidget,
    QLineEdit, QTextEdit, QLabel, QPushButton,
    QDialog, QFormLayout, QFileDialog, QMessageBox,
    QMenu, QInputDialog, QProgressDialog, QScrollArea,
    QFrame, QGridLayout, QToolButton, QApplication
)
from PySide6.QtGui import QAction, QKeySequence, QShortcut

from qfluentwidgets import (
    FluentIcon, CardWidget, PrimaryPushButton, PushButton,
    LineEdit, TextEdit, ListWidget, InfoBar, InfoBarPosition,
    SubtitleLabel, BodyLabel, CaptionLabel, SearchLineEdit,
    RoundMenu, Action, MenuAnimationType, ToolTipFilter,
    TransparentToolButton, IconWidget, FlowLayout,
    SmoothScrollArea, ElevatedCardWidget, PillPushButton,
    IndeterminateProgressRing, MessageBoxBase
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.projects_manager import ProjectsManager, Project, ProjectContext, ProjectChatSession, ContextType
from src.context_ingestion import get_ingestion_engine, IngestionResult
from src.markdown_display import ScrollableMarkdownDisplay


class ProjectListWidget(QWidget):
    """Sidebar widget showing list of projects"""

    project_selected = Signal(int)  # Emits project_id
    project_created = Signal()
    project_deleted = Signal(int)

    def __init__(self, projects_manager: ProjectsManager, parent=None):
        super().__init__(parent)
        self.projects_manager = projects_manager
        self.current_project_id: Optional[int] = None

        self._init_ui()
        self.refresh_projects()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        title = SubtitleLabel("Projects")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header_layout.addWidget(title)

        # New project button
        new_btn = TransparentToolButton(FluentIcon.ADD)
        new_btn.setToolTip("Create New Project")
        new_btn.clicked.connect(self._create_new_project)
        header_layout.addWidget(new_btn)

        layout.addLayout(header_layout)

        # Search box
        self.search_box = SearchLineEdit()
        self.search_box.setPlaceholderText("Search projects...")
        self.search_box.textChanged.connect(self._filter_projects)
        layout.addWidget(self.search_box)

        # Projects list
        self.list_widget = ListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

        # Styling
        self.setStyleSheet("""
            ProjectListWidget {
                background-color: #0d1117;
                border-right: 1px solid #30363d;
            }
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: #161b22;
                border-radius: 8px;
                padding: 12px;
                margin: 4px 0px;
                color: #c9d1d9;
            }
            QListWidget::item:selected {
                background-color: #1f6feb;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #21262d;
            }
            QListWidget::item:selected:hover {
                background-color: #388bfd;
            }
        """)

    def refresh_projects(self):
        """Refresh the projects list"""
        self.list_widget.clear()
        projects = self.projects_manager.get_all_projects()

        for project in projects:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, project.id)
            item.setText(project.name)
            item.setToolTip(project.description or "No description")
            self.list_widget.addItem(item)

            # Select first project if none selected
            if self.current_project_id is None and projects:
                self.current_project_id = projects[0].id
                self.list_widget.setCurrentItem(item)
                self.project_selected.emit(self.current_project_id)

    def _filter_projects(self, text: str):
        """Filter projects by search text"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle project selection"""
        project_id = item.data(Qt.UserRole)
        self.current_project_id = project_id
        self.project_selected.emit(project_id)

    def _show_context_menu(self, position):
        """Show context menu for project"""
        item = self.list_widget.itemAt(position)
        if not item:
            return

        menu = RoundMenu(parent=self)

        rename_action = Action(FluentIcon.EDIT, "Rename")
        rename_action.triggered.connect(lambda: self._rename_project(item))
        menu.addAction(rename_action)

        delete_action = Action(FluentIcon.DELETE, "Delete")
        delete_action.triggered.connect(lambda: self._delete_project(item))
        menu.addAction(delete_action)

        menu.exec(self.list_widget.mapToGlobal(position))

    def _create_new_project(self):
        """Create a new project"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Project")
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)

        name_input = LineEdit()
        name_input.setPlaceholderText("Project name...")
        layout.addRow("Name:", name_input)

        desc_input = TextEdit()
        desc_input.setPlaceholderText("Optional description...")
        desc_input.setMaximumHeight(100)
        layout.addRow("Description:", desc_input)

        btn_layout = QHBoxLayout()
        create_btn = PrimaryPushButton("Create")
        create_btn.clicked.connect(dialog.accept)
        cancel_btn = PushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_input.text().strip()
            if name:
                description = desc_input.toPlainText().strip()
                project = self.projects_manager.create_project(name, description)
                self.refresh_projects()
                self.project_created.emit()

                # Select the new project
                for i in range(self.list_widget.count()):
                    item = self.list_widget.item(i)
                    if item.data(Qt.UserRole) == project.id:
                        self.list_widget.setCurrentItem(item)
                        self.project_selected.emit(project.id)
                        break

    def _rename_project(self, item: QListWidgetItem):
        """Rename a project"""
        project_id = item.data(Qt.UserRole)
        current_name = item.text()

        new_name, ok = QInputDialog.getText(
            self, "Rename Project", "New name:", text=current_name
        )

        if ok and new_name.strip():
            self.projects_manager.update_project(project_id, name=new_name.strip())
            self.refresh_projects()

    def _delete_project(self, item: QListWidgetItem):
        """Delete a project"""
        project_id = item.data(Qt.UserRole)
        project_name = item.text()

        # Confirm deletion
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Delete Project")
        msg_box.setText(f"Are you sure you want to delete '{project_name}'?")
        msg_box.setInformativeText("This will delete all context and chat history.")
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            self.projects_manager.delete_project(project_id)
            self.project_deleted.emit(project_id)
            self.refresh_projects()


class ContextPanelWidget(QWidget):
    """Panel for managing project context (files, URLs, text, images)"""

    context_added = Signal()
    context_removed = Signal()

    def __init__(self, projects_manager: ProjectsManager, parent=None):
        super().__init__(parent)
        self.projects_manager = projects_manager
        self.current_project_id: Optional[int] = None
        self.ingestion_engine = get_ingestion_engine()

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Header
        header = SubtitleLabel("Context & Sources")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        layout.addWidget(header)

        # Add context buttons
        btn_layout = QHBoxLayout()

        file_btn = PushButton("Add File")
        file_btn.setIcon(FluentIcon.FOLDER)
        file_btn.clicked.connect(self._add_file_context)
        btn_layout.addWidget(file_btn)

        url_btn = PushButton("Add URL")
        url_btn.setIcon(FluentIcon.GLOBE)
        url_btn.clicked.connect(self._add_url_context)
        btn_layout.addWidget(url_btn)

        text_btn = PushButton("Add Text")
        text_btn.setIcon(FluentIcon.DOCUMENT)
        text_btn.clicked.connect(self._add_text_context)
        btn_layout.addWidget(text_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Context list
        self.context_list = ListWidget()
        self.context_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.context_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.context_list)

        # Styling
        self.setStyleSheet("""
            ContextPanelWidget {
                background-color: #0d1117;
            }
            QListWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
            QListWidget::item {
                background-color: #21262d;
                border-radius: 6px;
                padding: 10px;
                margin: 4px;
                color: #c9d1d9;
            }
            QListWidget::item:hover {
                background-color: #30363d;
            }
        """)

    def set_project(self, project_id: int):
        """Set the current project and refresh context"""
        self.current_project_id = project_id
        self.refresh_context()

    def refresh_context(self):
        """Refresh the context list for current project"""
        self.context_list.clear()

        if self.current_project_id is None:
            return

        contexts = self.projects_manager.get_project_context(self.current_project_id)

        for ctx in contexts:
            item = QListWidgetItem()

            # Format display based on type
            icon_map = {
                "file": FluentIcon.DOCUMENT,
                "url": FluentIcon.GLOBE,
                "text": FluentIcon.EDIT,
                "image": FluentIcon.PHOTO,
            }

            type_label = ctx.context_type.upper()
            source = ctx.source
            if len(source) > 50:
                source = source[:47] + "..."

            preview = ctx.content[:100].replace("\n", " ") if ctx.content else ""
            if len(preview) > 80:
                preview = preview[:77] + "..."

            item.setText(f"[{type_label}] {source}\n{preview}")
            item.setData(Qt.UserRole, ctx.id)
            item.setToolTip(f"Added: {ctx.created_at}")
            self.context_list.addItem(item)

    def _add_file_context(self):
        """Add file(s) as context"""
        if self.current_project_id is None:
            InfoBar.warning("No Project", "Please select a project first", parent=self)
            return

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files",
            str(Path.home()),
            "All Supported Files (*.txt *.md *.py *.js *.html *.css *.json *.xml *.yaml *.yml *.csv *.pdf *.docx *.doc *.png *.jpg *.jpeg *.gif);;Text Files (*.txt *.md);;Code Files (*.py *.js *.html *.css *.json *.xml *.yaml *.yml);;Documents (*.pdf *.docx *.doc);;Images (*.png *.jpg *.jpeg *.gif);;All Files (*)"
        )

        if not file_paths:
            return

        self._process_files(file_paths)

    def _process_files(self, file_paths: List[str]):
        """Process and ingest files"""
        progress = QProgressDialog("Processing files...", "Cancel", 0, len(file_paths), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        for i, file_path in enumerate(file_paths):
            if progress.wasCanceled():
                break

            progress.setValue(i)
            progress.setLabelText(f"Processing {Path(file_path).name}...")

            # Ingest file
            result = self.ingestion_engine.ingest_file(file_path)

            if result.success:
                self.projects_manager.add_context(
                    project_id=self.current_project_id,
                    context_type=ContextType.FILE if result.metadata.get("file_type") != "image" else ContextType.IMAGE,
                    source=result.metadata.get("filename", file_path),
                    content=result.content,
                    metadata=result.metadata
                )
            else:
                InfoBar.error(
                    "Import Failed",
                    f"Could not import {Path(file_path).name}: {result.error}",
                    parent=self,
                    duration=3000
                )

        progress.setValue(len(file_paths))
        self.refresh_context()
        self.context_added.emit()

        InfoBar.success(
            "Files Added",
            f"Added {len(file_paths)} file(s) to project",
            parent=self,
            duration=2000
        )

    def _add_url_context(self):
        """Add URL as context"""
        if self.current_project_id is None:
            InfoBar.warning("No Project", "Please select a project first", parent=self)
            return

        url, ok = QInputDialog.getText(
            self, "Add URL", "Enter URL:"
        )

        if not ok or not url.strip():
            return

        # Process URL
        progress = IndeterminateProgressRing(self)
        progress.setFixedSize(40, 40)
        progress.move(self.width() // 2 - 20, self.height() // 2 - 20)
        progress.show()

        # Run in background
        self._process_url_async(url.strip())

    def _process_url_async(self, url: str):
        """Process URL in background thread"""
        class URLWorker(QThread):
            finished = Signal(IngestionResult)

            def __init__(self, engine, url):
                super().__init__()
                self.engine = engine
                self.url = url

            def run(self):
                result = self.engine.ingest_url(self.url)
                self.finished.emit(result)

        self.worker = URLWorker(self.ingestion_engine, url)
        self.worker.finished.connect(self._on_url_processed)
        self.worker.start()

    def _on_url_processed(self, result: IngestionResult):
        """Handle URL processing completion"""
        if result.success:
            self.projects_manager.add_context(
                project_id=self.current_project_id,
                context_type=ContextType.URL,
                source=result.metadata.get("url", ""),
                content=result.content,
                metadata=result.metadata
            )
            self.refresh_context()
            self.context_added.emit()
            InfoBar.success("URL Added", "Article content extracted", parent=self, duration=2000)
        else:
            InfoBar.error("URL Failed", result.error or "Could not process URL", parent=self, duration=3000)

    def _add_text_context(self):
        """Add custom text as context"""
        if self.current_project_id is None:
            InfoBar.warning("No Project", "Please select a project first", parent=self)
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Text Note")
        dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout(dialog)

        title_input = LineEdit()
        title_input.setPlaceholderText("Note title (optional)...")
        layout.addWidget(title_input)

        text_edit = TextEdit()
        text_edit.setPlaceholderText("Enter your text here...")
        layout.addWidget(text_edit)

        btn_layout = QHBoxLayout()
        add_btn = PrimaryPushButton("Add")
        add_btn.clicked.connect(dialog.accept)
        cancel_btn = PushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = text_edit.toPlainText().strip()
            if text:
                title = title_input.text().strip() or "Text Note"
                result = self.ingestion_engine.ingest_text(text, title)

                self.projects_manager.add_context(
                    project_id=self.current_project_id,
                    context_type=ContextType.TEXT,
                    source=title,
                    content=result.content,
                    metadata=result.metadata
                )
                self.refresh_context()
                self.context_added.emit()
                InfoBar.success("Text Added", "Note added to project", parent=self, duration=2000)

    def _show_context_menu(self, position):
        """Show context menu for context item"""
        item = self.context_list.itemAt(position)
        if not item:
            return

        context_id = item.data(Qt.UserRole)

        menu = RoundMenu(parent=self)

        view_action = Action(FluentIcon.VIEW, "View Content")
        view_action.triggered.connect(lambda: self._view_context(context_id))
        menu.addAction(view_action)

        menu.addSeparator()

        delete_action = Action(FluentIcon.DELETE, "Remove")
        delete_action.triggered.connect(lambda: self._remove_context(context_id))
        menu.addAction(delete_action)

        menu.exec(self.context_list.mapToGlobal(position))

    def _view_context(self, context_id: int):
        """View full context content"""
        context = self.projects_manager.get_context(context_id)
        if not context:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Context: {context.source}")
        dialog.setMinimumSize(600, 500)

        layout = QVBoxLayout(dialog)

        # Metadata
        meta_label = CaptionLabel(
            f"Type: {context.context_type} | Added: {context.created_at}"
        )
        layout.addWidget(meta_label)

        # Content
        text_edit = TextEdit()
        text_edit.setPlainText(context.content)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        close_btn = PushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec()

    def _remove_context(self, context_id: int):
        """Remove context from project"""
        self.projects_manager.delete_context(context_id)
        self.refresh_context()
        self.context_removed.emit()
        InfoBar.success("Removed", "Context removed from project", parent=self, duration=2000)


class ChatWidget(QWidget):
    """Chat interface for projects with context-aware conversations"""

    def __init__(self, projects_manager: ProjectsManager, main_window=None, parent=None):
        super().__init__(parent)
        self.projects_manager = projects_manager
        self.main_window = main_window
        self.current_project_id: Optional[int] = None
        self.current_session_id: Optional[int] = None
        self.conversation_history: List[dict] = []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Chat header with session selector
        header = QWidget()
        header.setStyleSheet("background-color: #161b22; border-bottom: 1px solid #30363d;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(15, 10, 15, 10)

        self.session_label = SubtitleLabel("New Chat")
        self.session_label.setStyleSheet("font-size: 16px; color: white;")
        header_layout.addWidget(self.session_label)

        header_layout.addStretch()

        new_chat_btn = TransparentToolButton(FluentIcon.ADD)
        new_chat_btn.setToolTip("New Chat")
        new_chat_btn.clicked.connect(self._create_new_chat)
        header_layout.addWidget(new_chat_btn)

        layout.addWidget(header)

        # Chat messages area
        self.scroll_area = SmoothScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #0d1117; border: none;")

        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.setSpacing(15)
        self.messages_layout.setContentsMargins(20, 20, 20, 20)

        self.scroll_area.setWidget(self.messages_widget)
        layout.addWidget(self.scroll_area)

        # Input area
        input_widget = QWidget()
        input_widget.setStyleSheet("background-color: #161b22; border-top: 1px solid #30363d;")
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(20, 15, 20, 15)
        input_layout.setSpacing(10)

        # Text input
        self.message_input = TextEdit()
        self.message_input.setPlaceholderText("Message with project context...")
        self.message_input.setMaximumHeight(120)
        self.message_input.setStyleSheet("""
            TextEdit {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 10px;
                color: #c9d1d9;
            }
        """)
        input_layout.addWidget(self.message_input)

        # Send button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.send_btn = PrimaryPushButton("Send")
        self.send_btn.setIcon(FluentIcon.SEND)
        self.send_btn.clicked.connect(self._send_message)
        btn_layout.addWidget(self.send_btn)

        input_layout.addLayout(btn_layout)
        layout.addWidget(input_widget)

        # Shortcut for sending
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut.activated.connect(self._send_message)

    def set_project(self, project_id: int):
        """Set the current project"""
        self.current_project_id = project_id

        # Create new session for this project
        if project_id:
            session = self.projects_manager.create_chat_session(project_id)
            self.current_session_id = session.id
            self.session_label.setText(session.name)
            self._load_session_messages()
        else:
            self.current_session_id = None
            self.session_label.setText("New Chat")
            self._clear_messages()

    def _create_new_chat(self):
        """Create a new chat session"""
        if not self.current_project_id:
            return

        session = self.projects_manager.create_chat_session(self.current_project_id)
        self.current_session_id = session.id
        self.session_label.setText(session.name)
        self._clear_messages()
        self.conversation_history = []

    def _clear_messages(self):
        """Clear all messages from display"""
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _load_session_messages(self):
        """Load messages from current session"""
        self._clear_messages()

        if not self.current_session_id:
            return

        messages = self.projects_manager.get_chat_messages(self.current_session_id)
        self.conversation_history = []

        for msg in messages:
            self._add_message_to_display(msg.role, msg.content)
            self.conversation_history.append({
                "role": msg.role,
                "content": msg.content
            })

    def _add_message_to_display(self, role: str, content: str):
        """Add a message bubble to the chat display"""
        is_user = role == "user"

        # Message container
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(10)

        # Avatar
        avatar = IconWidget()
        avatar.setFixedSize(32, 32)
        if is_user:
            avatar.setStyleSheet("""
                background-color: #1f6feb;
                border-radius: 16px;
            """)
        else:
            avatar.setStyleSheet("""
                background-color: #238636;
                border-radius: 16px;
            """)

        # Message bubble
        bubble = QWidget()
        bubble.setStyleSheet(f"""
            QWidget {{
                background-color: {'#1f6feb' if is_user else '#21262d'};
                border-radius: 12px;
                padding: 12px;
            }}
        """)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 12, 12, 12)

        # Role label
        role_label = CaptionLabel("You" if is_user else "AI")
        role_label.setStyleSheet(f"color: {'#ffffff' if is_user else '#8b949e'}; font-weight: bold;")
        bubble_layout.addWidget(role_label)

        # Content
        if is_user:
            content_label = BodyLabel(content)
            content_label.setWordWrap(True)
            content_label.setStyleSheet("color: white;")
            content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            bubble_layout.addWidget(content_label)
        else:
            # Use markdown for AI responses
            content_widget = ScrollableMarkdownDisplay()
            content_widget.set_content(content)
            content_widget.setStyleSheet("background-color: transparent;")
            bubble_layout.addWidget(content_widget)

        # Layout arrangement
        if is_user:
            container_layout.addStretch()
            container_layout.addWidget(bubble)
            container_layout.addWidget(avatar)
        else:
            container_layout.addWidget(avatar)
            container_layout.addWidget(bubble)
            container_layout.addStretch()

        self.messages_layout.addWidget(container)

        # Scroll to bottom
        QApplication.processEvents()
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def _send_message(self):
        """Send message and get AI response"""
        if not self.current_project_id or not self.current_session_id:
            InfoBar.warning("No Project", "Please select a project first", parent=self)
            return

        message = self.message_input.toPlainText().strip()
        if not message:
            return

        # Clear input
        self.message_input.clear()

        # Add user message to display
        self._add_message_to_display("user", message)

        # Save to database
        self.projects_manager.add_chat_message(self.current_session_id, "user", message)
        self.conversation_history.append({"role": "user", "content": message})

        # Show typing indicator
        self.send_btn.setEnabled(False)
        self.send_btn.setText("Thinking...")

        # Generate response with context
        self._generate_response(message)

    def _generate_response(self, user_message: str):
        """Generate AI response with project context"""
        # Get context for this project
        context_text = self.projects_manager.get_context_text_for_llm(self.current_project_id)

        # Build system prompt with context
        system_prompt = self._build_system_prompt(context_text)

        # Run in background thread
        class ResponseWorker(QThread):
            response_ready = Signal(str)
            error_occurred = Signal(str)

            def __init__(self, main_window, system_prompt, history, message):
                super().__init__()
                self.main_window = main_window
                self.system_prompt = system_prompt
                self.history = history
                self.message = message

            def run(self):
                try:
                    if self.main_window and hasattr(self.main_window, 'llm_manager'):
                        llm = self.main_window.llm_manager

                        # Build messages
                        messages = [{"role": "system", "content": self.system_prompt}]
                        messages.extend(self.history[-10:])  # Last 10 messages
                        messages.append({"role": "user", "content": self.message})

                        response = llm._make_groq_api_call(messages)
                        self.response_ready.emit(response)
                    else:
                        self.error_occurred.emit("LLM manager not available")

                except Exception as e:
                    self.error_occurred.emit(str(e))

        self.response_worker = ResponseWorker(
            self.main_window,
            system_prompt,
            self.conversation_history,
            user_message
        )
        self.response_worker.response_ready.connect(self._on_response_ready)
        self.response_worker.error_occurred.connect(self._on_response_error)
        self.response_worker.start()

    def _build_system_prompt(self, context_text: str) -> str:
        """Build system prompt with project context"""
        base_prompt = """You are a helpful AI assistant with access to project-specific context. 
Use the provided context to give accurate, relevant responses. 
If the context doesn't contain relevant information, say so clearly.

PROJECT CONTEXT:
"""

        if context_text:
            base_prompt += context_text
        else:
            base_prompt += "(No context added yet)"

        base_prompt += """

INSTRUCTIONS:
- Answer based on the provided context when relevant
- Be concise but thorough
- If asked about something not in context, indicate that clearly
- Cite specific sources from the context when appropriate"""

        return base_prompt

    def _on_response_ready(self, response: str):
        """Handle AI response"""
        self._add_message_to_display("assistant", response)
        self.projects_manager.add_chat_message(self.current_session_id, "assistant", response)
        self.conversation_history.append({"role": "assistant", "content": response})

        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")

    def _on_response_error(self, error: str):
        """Handle response error"""
        InfoBar.error("Error", f"Failed to get response: {error}", parent=self, duration=5000)
        self.send_btn.setEnabled(True)
        self.send_btn.setText("Send")


class ProjectsPage(QWidget):
    """Main Projects page - Perplexity-like Spaces feature"""

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setObjectName("ProjectsPage")

        # Initialize managers
        self.projects_manager = ProjectsManager()

        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left sidebar - Project list
        self.project_list = ProjectListWidget(self.projects_manager)
        self.project_list.setMinimumWidth(250)
        self.project_list.setMaximumWidth(350)
        self.project_list.project_selected.connect(self._on_project_selected)
        splitter.addWidget(self.project_list)

        # Center - Context panel
        self.context_panel = ContextPanelWidget(self.projects_manager)
        self.context_panel.setMinimumWidth(300)
        self.context_panel.setMaximumWidth(450)
        splitter.addWidget(self.context_panel)

        # Right - Chat interface
        self.chat_widget = ChatWidget(self.projects_manager, self.main_window)
        splitter.addWidget(self.chat_widget)

        # Set splitter proportions
        splitter.setSizes([280, 350, 570])

        layout.addWidget(splitter)

        # Styling
        self.setStyleSheet("""
            ProjectsPage {
                background-color: #0a0f1d;
            }
        """)

    def _on_project_selected(self, project_id: int):
        """Handle project selection"""
        self.context_panel.set_project(project_id)
        self.chat_widget.set_project(project_id)
