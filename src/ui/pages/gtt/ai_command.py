"""
AI Command Dialog Module.
Provides AI-powered command generation using OmniProxy SDK.
"""
import json
from PySide6.QtCore import Signal, QTimer, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    SubtitleLabel, BodyLabel, PrimaryPushButton, PushButton,
    ComboBox, TextEdit, IndeterminateProgressRing, InfoBar
)
from .ai_generator import CommandGeneratorWorker, CommandResultHandler
class AICommandDialog(QWidget):
    """AI-powered command generator dialog using OmniProxy SDK."""
    command_generated = Signal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("✨ AI Command Generator")
        self.setModal(True)
        self.setMinimumWidth(650)
        self.setMinimumHeight(600)
        self.omniproxy_url = "http://127.0.0.1:8743"
        self.result_handler = CommandResultHandler()
        self.init_ui()
    def init_ui(self) -> None:
        """Initialize dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(SubtitleLabel("🤖 Describe What You Want to Accomplish"))
        desc = BodyLabel("Type a natural language description. The AI will generate GTT commands.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8b949e; font-size: 13px;")
        layout.addWidget(desc)
        self._create_model_selector(layout)
        self._create_input_section(layout)
        self._create_generate_button(layout)
        self._create_progress(layout)
        self._create_output_section(layout)
        self._create_actions(layout)
    def _create_model_selector(self, layout: QVBoxLayout) -> None:
        """Create model selector."""
        model_layout = QHBoxLayout()
        model_layout.addWidget(BodyLabel("AI Model:"))
        self.model_combo = ComboBox()
        self.model_combo.addItems([
            "minimax-m2.1 (Best for code & automation)", "qwen3-coder-plus (Fastest)",
            "kimi-k2 (Deep reasoning)", "deepseek-v3.2 (Balanced)",
        ])
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        layout.addLayout(model_layout)
    def _create_input_section(self, layout: QVBoxLayout) -> None:
        """Create description input."""
        layout.addWidget(BodyLabel("Your Description:"))
        self.description_input = TextEdit()
        self.description_input.setPlaceholderText("Examples:\n• 'Open Firefox and search for Python'\n• 'Focus VS Code, create new file'")
        self.description_input.setMinimumHeight(120)
        self._style_text_edit(self.description_input, "#1a1f26")
        layout.addWidget(self.description_input)
    def _create_generate_button(self, layout: QVBoxLayout) -> None:
        """Create generate button."""
        self.generate_btn = PrimaryPushButton("🚀 Generate Command")
        self.generate_btn.setStyleSheet("font-size: 14px; padding: 10px; min-height: 40px;")
        self.generate_btn.clicked.connect(self.generate_command)
        layout.addWidget(self.generate_btn)
    def _create_progress(self, layout: QVBoxLayout) -> None:
        """Create progress indicator."""
        self.progress = IndeterminateProgressRing()
        self.progress.setFixedSize(32, 32)
        self.progress.setVisible(False)
        layout.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignCenter)
    def _create_output_section(self, layout: QVBoxLayout) -> None:
        """Create output section."""
        layout.addWidget(BodyLabel("Generated Command:"))
        self.output_edit = TextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setMinimumHeight(120)
        self._style_text_edit(self.output_edit, "#0d1117")
        layout.addWidget(self.output_edit)
    def _create_actions(self, layout: QVBoxLayout) -> None:
        """Create action buttons."""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.copy_btn = PushButton("📋 Copy to Script")
        self.copy_btn.setMinimumHeight(35)
        self.copy_btn.clicked.connect(self.copy_to_script)
        btn_layout.addWidget(self.copy_btn)
        self.close_btn = PushButton("Close")
        self.close_btn.setMinimumHeight(35)
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
    def _style_text_edit(self, widget: TextEdit, bg_color: str) -> None:
        """Apply consistent text edit styling."""
        widget.setStyleSheet(f"""
            TextEdit {{ background-color: {bg_color}; border: 1px solid #30363d;
                border-radius: 8px; color: #e6edf3; padding: 10px;
                font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 12px; }}
            TextEdit:focus {{ border-color: #1f6feb; }}
        """)
    def get_model_id(self) -> str:
        """Get model ID from selected option."""
        model_map = {
            "minimax-m2.1 (Best for code & automation)": "minimax-m2.1",
            "qwen3-coder-plus (Fastest)": "qwen3-coder-plus",
            "kimi-k2 (Deep reasoning)": "kimi-k2",
            "deepseek-v3.2 (Balanced)": "deepseek-v3.2",
        }
        return model_map.get(self.model_combo.currentText(), "minimax-m2.1")
    def generate_command(self) -> None:
        """Generate command from description."""
        description = self.description_input.toPlainText().strip()
        if not description:
            InfoBar.warning("Empty Input", "Please describe what you want", parent=self, duration=2000)
            return
        self.generating = True
        self.generate_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.output_edit.clear()
        self.result_handler.reset()
        model_id = self.get_model_id()
        self.gen_thread = CommandGeneratorWorker(description, model_id, self.omniproxy_url)
        self.gen_thread.result_signal.connect(self.on_generation_complete)
        self.gen_thread.start()
    def on_generation_complete(self, result: str) -> None:
        """Handle generation complete."""
        def on_retry(count):
            InfoBar.info("Retrying", f"({count}/{self.result_handler.max_retries})", parent=self, duration=1500)
            QTimer.singleShot(500, self.generate_command)
        def on_success(result_text, commands):
            self._finish_generation(True, result_text)
        def on_error(error):
            self._finish_generation(False, error)
        self.result_handler.handle_result(result, on_retry, on_success, on_error)
    def _finish_generation(self, success: bool, result: str) -> None:
        """Finish generation and update UI."""
        self.generating = False
        self.generate_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.output_edit.setPlainText(result)
        if not success:
            InfoBar.error("Generation Failed", result, parent=self, duration=5000)
    def copy_to_script(self) -> None:
        """Copy generated command to script."""
        output = self.output_edit.toPlainText().strip()
        if not output:
            return
        try:
            commands = json.loads(output)
            if isinstance(commands, list):
                for cmd in commands:
                    self.command_generated.emit(cmd)
                InfoBar.success("Added to Script", f"Added {len(commands)} commands", parent=self, duration=2000)
                self.close()
            else:
                InfoBar.warning("Invalid Format", "Output is not a command list", parent=self, duration=2000)
        except Exception as e:
            InfoBar.error("Parse Error", str(e), parent=self, duration=3000)
