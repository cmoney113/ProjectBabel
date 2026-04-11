"""
Prompt Manager Dialog
Modal for managing LLM prompts (add, edit, delete)
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
)
from PySide6.QtCore import Signal, Qt
from qfluentwidgets import CardWidget, FluentIcon

from src.settings_manager import SettingsManager


class PromptManagerDialog(QDialog):
    """Modal dialog for managing LLM prompts"""

    # Signal emitted when prompts are changed
    prompts_changed = Signal()

    def __init__(self, settings_manager=None, parent=None):
        super().__init__(parent)
        self.settings_manager = (
            settings_manager if settings_manager else SettingsManager()
        )
        self.setWindowTitle("Manage Prompts")
        self.setMinimumSize(600, 500)
        self._init_ui()
        self._load_prompts()

    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header = QLabel("LLM Prompt Manager")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # Description
        desc = QLabel("Add, edit, or delete prompts that customize the LLM's behavior.")
        desc.setStyleSheet("color: #888;")
        layout.addWidget(desc)

        # Prompt list
        self.prompt_list = QListWidget()
        self.prompt_list.itemClicked.connect(self._on_prompt_selected)
        layout.addWidget(self.prompt_list)

        # Editor section
        editor_card = CardWidget()
        editor_layout = QVBoxLayout(editor_card)

        # Name field
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Prompt name (e.g., Casual, Professional)")
        name_layout.addWidget(self.name_input)
        editor_layout.addLayout(name_layout)

        # Content field
        editor_layout.addWidget(QLabel("Prompt Text:"))
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("Enter the prompt text...")
        self.content_input.setMinimumHeight(150)
        editor_layout.addWidget(self.content_input)

        layout.addWidget(editor_card)

        # Buttons
        button_layout = QHBoxLayout()

        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self._add_prompt)
        button_layout.addWidget(self.add_button)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save_prompt)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self._delete_prompt)
        self.delete_button.setEnabled(False)
        button_layout.addWidget(self.delete_button)

        button_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def _load_prompts(self):
        """Load prompts from settings"""
        self.prompt_list.clear()
        prompts = self.settings_manager.get_prompts()

        # prompts is Dict[str, str] - name -> content
        for prompt_name, prompt_content in prompts.items():
            item = QListWidgetItem(prompt_name)
            item.setData(Qt.UserRole, prompt_name)
            self.prompt_list.addItem(item)

    def _on_prompt_selected(self, item):
        """Handle prompt selection"""
        prompt_name = item.data(Qt.UserRole)
        prompts = self.settings_manager.get_prompts()

        if prompt_name in prompts:
            self.name_input.setText(prompt_name)
            self.content_input.setText(prompts[prompt_name])
            self.save_button.setEnabled(True)
            self.delete_button.setEnabled(True)

    def _add_prompt(self):
        """Add a new prompt"""
        name = self.name_input.text().strip()
        content = self.content_input.toPlainText().strip()

        if not name or not content:
            QMessageBox.warning(self, "Error", "Please enter both name and content")
            return

        # Generate a simple ID
        prompt_id = name.lower().replace(" ", "_")

        self.settings_manager.save_prompt(name, content)
        self._load_prompts()

        # Select the new prompt
        for i in range(self.prompt_list.count()):
            item = self.prompt_list.item(i)
            if item.data(Qt.UserRole) == prompt_id:
                self.prompt_list.setCurrentItem(item)
                break

        InfoBar.success("Success", f"Prompt '{name}' added", duration=2000, parent=self)

    def _save_prompt(self):
        """Save changes to selected prompt"""
        selected_items = self.prompt_list.selectedItems()
        if not selected_items:
            return

        prompt_id = selected_items[0].data(Qt.UserRole)
        name = self.name_input.text().strip()
        content = self.content_input.toPlainText().strip()

        if not name or not content:
            QMessageBox.warning(self, "Error", "Please enter both name and content")
            return

        self.settings_manager.save_prompt(name, content)
        self._load_prompts()

        # Re-select the item
        for i in range(self.prompt_list.count()):
            item = self.prompt_list.item(i)
            if item.data(Qt.UserRole) == prompt_id:
                self.prompt_list.setCurrentItem(item)
                break

        InfoBar.success("Success", f"Prompt '{name}' saved", duration=2000, parent=self)

    def _delete_prompt(self):
        """Delete selected prompt"""
        selected_items = self.prompt_list.selectedItems()
        if not selected_items:
            return

        prompt_id = selected_items[0].data(Qt.UserRole)
        prompt_name = selected_items[0].text()

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{prompt_name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.settings_manager.delete_prompt(prompt_id)
            self.name_input.clear()
            self.content_input.clear()
            self.save_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self._load_prompts()
            InfoBar.success(
                "Success", f"Prompt '{prompt_name}' deleted", duration=2000, parent=self
            )


# Import InfoBar for feedback messages
from qfluentwidgets import InfoBar
