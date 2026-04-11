"""
Script Builder Panel Component for GTT.
Provides command palette and script list for building automation sequences.
"""
from typing import Dict, Any
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import BodyLabel, PrimaryPushButton, InfoBar
from ..ai_command import AICommandDialog
from .script_params import ParamBuilderMixin
from .script_list_manager import ScriptListManager
from .script_builder_ui import ScriptBuilderUI
class ScriptBuilderPanel(QWidget, ParamBuilderMixin):
    """Script builder panel with command palette and script list."""
    command_added = Signal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window_list = []
        self._init_ui()
    def _init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(ScriptBuilderUI.create_title())
        self._create_command_row(layout)
        scroll, self.params_layout = ScriptBuilderUI.create_params_scroll()
        layout.addWidget(scroll)
        self._create_script_list(layout)
        self._create_controls(layout)
        self._create_execute_section(layout)
        self.command_type_combo.currentIndexChanged.connect(self.on_command_changed)
    def _create_command_row(self, layout: QVBoxLayout) -> None:
        """Create command selection with AI button."""
        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(BodyLabel("Command:"))
        self.command_type_combo = ScriptBuilderUI.create_command_combo(
            ScriptBuilderUI.get_commands()
        )
        cmd_layout.addWidget(self.command_type_combo)
        self.ai_btn = ScriptBuilderUI.create_ai_button()
        self.ai_btn.clicked.connect(self.show_ai_dialog)
        cmd_layout.addWidget(self.ai_btn)
        layout.addLayout(cmd_layout)
    def _create_script_list(self, layout: QVBoxLayout) -> None:
        """Create script list widget and manager."""
        from qfluentwidgets import StrongBodyLabel
        layout.addWidget(StrongBodyLabel("Script Commands"))
        self.script_list = ScriptBuilderUI.create_script_list()
        self.script_list.itemDoubleClicked.connect(self.remove_selected_command)
        layout.addWidget(self.script_list)
        self.list_manager = ScriptListManager(self.script_list)
    def _create_controls(self, layout: QVBoxLayout) -> None:
        """Create script control buttons."""
        controls = QHBoxLayout()
        buttons = ScriptBuilderUI.create_control_buttons()
        self.remove_btn = buttons['remove']
        self.remove_btn.clicked.connect(self.remove_selected_command)
        controls.addWidget(self.remove_btn)
        self.clear_btn = buttons['clear']
        self.clear_btn.clicked.connect(self.clear_script)
        controls.addWidget(self.clear_btn)
        self.export_btn = buttons['export']
        self.export_btn.clicked.connect(self.export_script)
        controls.addWidget(self.export_btn)
        self.import_btn = buttons['import']
        self.import_btn.clicked.connect(self.import_script)
        controls.addWidget(self.import_btn)
        controls.addStretch()
        layout.addLayout(controls)
    def _create_execute_section(self, layout: QVBoxLayout) -> None:
        """Create dry-run toggle and execute button."""
        dry_run = QHBoxLayout()
        dry_run.addWidget(BodyLabel("Dry-run mode:"))
        self.dry_run_switch = ScriptBuilderUI.create_dry_run_switch()
        dry_run.addWidget(self.dry_run_switch)
        dry_run.addStretch()
        layout.addLayout(dry_run)
        self.execute_btn = ScriptBuilderUI.create_execute_button()
        self.execute_btn.clicked.connect(self.execute_script)
        layout.addWidget(self.execute_btn)
        container, ring, label = ScriptBuilderUI.create_progress_indicator()
        self.progress_ring = ring
        self.progress_label = label
        self.progress_container = container
        layout.addWidget(self.progress_container)
    def on_command_changed(self, index: int) -> None:
        """Handle command type change."""
        self.clear_params_layout()
        self._build_params(self.command_type_combo.currentText())
    def _build_params(self, cmd_type: str) -> None:
        """Build parameter inputs for command type."""
        window_ops = ["Focus Window", "Close Window", "Maximize Window", "Minimize Window",
                      "Unmaximize Window", "Unminimize Window", "Activate Window"]
        if cmd_type in window_ops:
            self.build_window_selector()
        elif cmd_type == "Move Window":
            self.build_move_params()
        elif cmd_type == "Resize Window":
            self.build_resize_params()
        elif cmd_type == "Launch App":
            self.build_launch_params()
        elif cmd_type == "Type Text":
            self.build_text_params()
        elif cmd_type == "Send Keys":
            self.build_keys_params()
        elif cmd_type == "Screenshot":
            self.build_screenshot_params()
        elif cmd_type == "Wait":
            self.build_wait_params()
        elif cmd_type == "TermPipe Shell Command":
            self.build_termpipe_params()
    def show_ai_dialog(self) -> None:
        """Show AI command generator dialog."""
        dialog = AICommandDialog(self.parent())
        dialog.command_generated.connect(self.add_generated_command)
        dialog.show()
    def add_generated_command(self, cmd_data: Dict[str, Any]) -> None:
        """Add AI-generated command."""
        self.list_manager.add_command(cmd_data)
    def add_command(self) -> None:
        """Add current command to script."""
        cmd_data = {"type": self.command_type_combo.currentText(), "params": self.collect_params()}
        self.list_manager.add_command(cmd_data)
        InfoBar.success("Command Added", f"Added {cmd_data['type']}", parent=self.parent(), duration=1500)
    def remove_selected_command(self) -> None:
        """Remove selected command."""
        self.list_manager.remove_selected()
    def clear_script(self) -> None:
        """Clear all commands."""
        self.list_manager.clear()
        InfoBar.info("Script Cleared", "All commands removed", parent=self.parent(), duration=1500)
    def export_script(self) -> None:
        """Export script to JSON."""
        self.list_manager.export_script(self.parent())
    def import_script(self) -> None:
        """Import script from JSON."""
        self.list_manager.import_script(self.parent())
    def execute_script(self) -> None:
        """Execute or preview script."""
        if self.list_manager.is_empty():
            InfoBar.warning("Empty Script", "Add commands first", parent=self.parent(), duration=2000)
            return
        if hasattr(self.parent(), 'on_execute_script'):
            self.parent().on_execute_script(
                self.list_manager.get_commands(), self.dry_run_switch.isChecked()
            )
