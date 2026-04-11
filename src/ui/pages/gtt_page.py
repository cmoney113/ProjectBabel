"""
GTT (GreaterTouchTool) Page - Window automation and macro execution interface
Provides NLP-driven window management, script building, and voice-controlled automation

Enterprise RPA Features:
- Auto-accept Wayland Remote Desktop permission modal via uinput
- Full window management, hotkeys, macros, and GNOME Shell integration
- Vision & AI traversal operations for headless UI automation
- Real-time event subscriptions for workflow monitoring

Refactored Architecture:
- Modular widget components (ConsoleOutputPanel, ScriptBuilderPanel, etc.)
- Tab-based main content area for better organization
- Proper scrolling and space management
- Fluent Design components with consistent sizing
"""

import json
import subprocess
import requests
import os
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any

from PySide6.QtCore import Qt, QTimer, Signal, QThread, QProcess, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, 
    QListWidget, QListWidgetItem, QSpinBox, QSplitter, 
    QFileDialog, QMessageBox, QTabWidget, QGroupBox, QGridLayout
)
from qfluentwidgets import (
    SubtitleLabel, BodyLabel, StrongBodyLabel, CaptionLabel,
    PrimaryPushButton, PushButton, ToggleButton, ComboBox, 
    LineEdit, CardWidget, InfoBar, IndeterminateProgressRing, 
    TransparentToolButton, FluentIcon, TextEdit, StrongBodyLabel, 
    SwitchButton, ProgressBar, MessageBox, SearchLineEdit,
    FluentStyleSheet, isDarkTheme
)


# ============================================================================
# KernClip Bus Client - High-speed IPC (89k ops/sec, 4.2 Gbps)
# ============================================================================

class BusClient:
    """KernClip Bus client for high-speed IPC"""

    def __init__(self):
        self.socket_path = f"/run/user/{os.getuid()}/kernclip-bus.sock"
        self.available = False
        self._check_availability()

    def _check_availability(self):
        """Check if kernclip-busd is running"""
        try:
            self.available = os.path.exists(self.socket_path)
        except Exception:
            self.available = False

    def pub(self, topic: str, data: str, mime: str = "text/plain") -> bool:
        """Publish data to a topic"""
        if not self.available:
            return False
        try:
            import socket
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(self.socket_path)
            msg = json.dumps({"op": "pub", "topic": topic, "mime": mime, "data": data}) + "\n"
            s.sendall(msg.encode())
            response = b""
            while b"\n" not in response:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
            s.close()
            result = json.loads(response.decode())
            return result.get("ok", False)
        except Exception:
            self.available = False
            return False

    def get(self, topic: str, after_seq: int = None) -> dict:
        """Get latest message from a topic"""
        if not self.available:
            return None
        try:
            import socket
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(self.socket_path)
            req = {"op": "get", "topic": topic}
            if after_seq:
                req["after_seq"] = after_seq
            msg = json.dumps(req) + "\n"
            s.sendall(msg.encode())
            response = b""
            while b"\n" not in response:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
            s.close()
            result = json.loads(response.decode())
            return result if result.get("ok") else None
        except Exception:
            return None


# ============================================================================
# GTT Startup Thread - Background daemon initialization
# ============================================================================

class GTTStartupThread(QThread):
    """Background thread for GTT daemon startup sequence"""
    status_signal = Signal(str, str)  # title, message
    completed_signal = Signal(bool)   # success

    def __init__(self):
        super().__init__()
        self.portal_process = None

    def run(self):
        """Execute GTT startup sequence with modal auto-acceptance"""
        try:
            self.status_signal.emit("Starting GTT Portal", "Launching Remote Desktop portal...")
            self.portal_process = subprocess.Popen(
                ["gtt-portal"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.status_signal.emit("Accepting Permission", "Auto-accepting Wayland RD modal...")
            QTimer.singleShot(40, self.accept_modal)
            self.msleep(150)
            
            self.status_signal.emit("Starting Daemon", "Launching gttuni daemon...")
            result = subprocess.run(["gttuni", "--daemon"], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                self.status_signal.emit("GTT Ready", "Daemon started successfully")
                self.completed_signal.emit(True)
            else:
                self.status_signal.emit("Daemon Error", result.stderr or "Unknown error")
                self.completed_signal.emit(False)
        except subprocess.TimeoutExpired:
            self.status_signal.emit("Startup Timeout", "Process timed out")
            self.completed_signal.emit(False)
        except Exception as e:
            self.status_signal.emit("Startup Failed", str(e))
            self.completed_signal.emit(False)

    def accept_modal(self):
        """Execute uinput key sequence to accept RD modal"""
        try:
            subprocess.run(
                'echo "key space,,pause 15,,tab,,tab,,space" | wbind',
                shell=True, capture_output=True, timeout=2
            )
        except Exception as e:
            self.status_signal.emit("Modal Acceptance Failed", str(e))


# ============================================================================
# AI Command Generator Dialog
# ============================================================================

class AICommandDialog(QWidget):
    """AI-powered command generator dialog using OmniProxy SDK"""
    command_generated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("✨ AI Command Generator")
        self.setModal(True)
        self.setMinimumWidth(650)
        self.setMinimumHeight(600)
        self.omniproxy_url = "http://127.0.0.1:8743"
        self.generating = False
        self.retry_count = 0
        self.max_retries = 2
        self.init_ui()

    def init_ui(self):
        """Initialize the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title = SubtitleLabel("🤖 Describe What You Want to Accomplish")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        layout.addWidget(title)

        desc = BodyLabel("Type a natural language description. The AI will generate the complete GTT command sequence.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8b949e; font-size: 13px;")
        layout.addWidget(desc)

        # Model selector
        model_layout = QHBoxLayout()
        model_layout.addWidget(BodyLabel("AI Model:"))
        self.model_combo = ComboBox()
        self.model_combo.addItems([
            "minimax-m2.1 (Best for code & automation)",
            "qwen3-coder-plus (Fastest)",
            "kimi-k2 (Deep reasoning)",
            "deepseek-v3.2 (Balanced)",
        ])
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        layout.addLayout(model_layout)

        # Input
        layout.addWidget(BodyLabel("Your Description:"))
        self.description_input = TextEdit()
        self.description_input.setPlaceholderText(
            "Examples:\n"
            "• 'Open Firefox, navigate to google.com, and search for Python tutorials'\n"
            "• 'Focus VS Code, create a new file, and type out a hello world program'\n"
            "• 'Arrange my windows: VS Code on left 50%, browser on right 50%'"
        )
        self.description_input.setMinimumHeight(120)
        self._style_text_edit(self.description_input, "#1a1f26")
        layout.addWidget(self.description_input)

        # Generate button
        self.generate_btn = PrimaryPushButton("🚀 Generate Command")
        self.generate_btn.setStyleSheet("font-size: 14px; padding: 10px; min-height: 40px;")
        self.generate_btn.clicked.connect(self.generate_command)
        layout.addWidget(self.generate_btn)

        # Progress
        self.progress = IndeterminateProgressRing()
        self.progress.setFixedSize(32, 32)
        self.progress.setVisible(False)
        layout.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignCenter)

        # Output
        layout.addWidget(BodyLabel("Generated Command:"))
        self.output_edit = TextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setMinimumHeight(120)
        self._style_text_edit(self.output_edit, "#0d1117")
        layout.addWidget(self.output_edit)

        # Actions
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

    def _style_text_edit(self, widget, bg_color):
        """Apply consistent text edit styling"""
        widget.setStyleSheet(f"""
            TextEdit {{
                background-color: {bg_color};
                border: 1px solid #30363d;
                border-radius: 8px;
                color: #e6edf3;
                padding: 10px;
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
                font-size: 12px;
            }}
            TextEdit:focus {{ border-color: #1f6feb; }}
        """)

    def get_model_id(self):
        """Get model ID from selected option"""
        model_map = {
            "minimax-m2.1 (Best for code & automation)": "minimax-m2.1",
            "qwen3-coder-plus (Fastest)": "qwen3-coder-plus",
            "kimi-k2 (Deep reasoning)": "kimi-k2",
            "deepseek-v3.2 (Balanced)": "deepseek-v3.2",
        }
        return model_map.get(self.model_combo.currentText(), "minimax-m2.1")

    async def generate_with_omniproxy(self, description, model_id):
        """Generate command using OmniProxy SDK"""
        try:
            import sys
            sys.path.insert(0, "/home/craig/new-projects/omniproxy/sdk/python")
            from omniproxy import OmniProxy, Message

            system_prompt = """You are a GTT (GreaterTouchTool) command generator. Convert natural language descriptions into GTT command sequences.

GTT Commands: focus, close, maximize, minimize, move-window, resize-window, launch, type, key, 
cb, cb-set, cb-paste, sc, ocr, ocr-file, sl, rl, snap, hotkey-script, hotkey-input, macro-add, 
macro-remove, eval, notify, vision-scan, vision-map, vision-click, sub-mouse, sub-window, etc.

Examples:
- "Open Firefox" → launch Firefox
- "Type hello and press enter" → type hello, key enter
- "Screenshot to /tmp/test.png" → sc /tmp/test.png

Rules: Be concise, output commands only, use "Wait" between actions that need time."""

            client = OmniProxy(base_url=self.omniproxy_url)
            async with client:
                response = await client.chat.completions.create(
                    model=model_id,
                    messages=[
                        Message(role="system", content=system_prompt),
                        Message(role="user", content=description)
                    ],
                    temperature=0.7,
                    max_tokens=2048,
                    timeout=30
                )
            return response.choices[0].message.content
        except Exception as e:
            error_msg = str(e)
            if self.retry_count < self.max_retries and ("timeout" in error_msg.lower() or "connection" in error_msg.lower()):
                self.retry_count += 1
                return f"RETRY:{error_msg}"
            return f"Error: {error_msg}"

    def generate_command(self):
        """Generate command from description"""
        description = self.description_input.toPlainText().strip()
        if not description:
            InfoBar.warning("Empty Input", "Please describe what you want to accomplish", parent=self, duration=2000)
            return

        self.generating = True
        self.generate_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.output_edit.clear()
        self.retry_count = 0

        model_id = self.get_model_id()

        class GenerationThread(QThread):
            result_signal = Signal(str)
            def __init__(self, desc, model, dialog):
                super().__init__()
                self.desc = desc
                self.model = model
                self.dialog = dialog
            def run(self):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(self.dialog.generate_with_omniproxy(self.desc, self.model))
                    self.result_signal.emit(result)
                finally:
                    loop.close()

        self.gen_thread = GenerationThread(description, model_id, self)
        self.gen_thread.result_signal.connect(self.on_generation_complete)
        self.gen_thread.start()

    def on_generation_complete(self, result):
        """Handle generation complete"""
        if result.startswith("RETRY:"):
            self.retry_count += 1
            if self.retry_count <= self.max_retries:
                InfoBar.info("Retrying", f"({self.retry_count}/{self.max_retries})", parent=self, duration=1500)
                QTimer.singleShot(500, lambda: self.generate_command())
                return
            else:
                error_msg = result.replace("RETRY:", "")
                self._finish_generation(False, error_msg)
                return
        self._finish_generation(True, result)

    def _finish_generation(self, success, result):
        """Finish generation and update UI"""
        self.generating = False
        self.generate_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.output_edit.setPlainText(result)
        
        if not success:
            InfoBar.error("Generation Failed", result, parent=self, duration=5000)
            return

        try:
            commands = json.loads(result)
            if isinstance(commands, list):
                InfoBar.success("Command Generated", f"Generated {len(commands)} commands", parent=self, duration=3000)
            else:
                InfoBar.warning("Invalid Format", "Generated output is not a command list", parent=self, duration=3000)
        except json.JSONDecodeError:
            if result.startswith("Error:"):
                InfoBar.error("API Error", result, parent=self, duration=5000)
            else:
                InfoBar.warning("Parse Error", "Generated output is not valid JSON", parent=self, duration=3000)

    def copy_to_script(self):
        """Copy generated command to script"""
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
                InfoBar.warning("Invalid Format", "Generated output is not a command list", parent=self, duration=2000)
        except Exception as e:
            InfoBar.error("Parse Error", str(e), parent=self, duration=3000)


# ============================================================================
# Hotkey Manager Dialog
# ============================================================================

class HotkeyManagerDialog(QWidget):
    """Dialog for managing GTT hotkeys"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⌨️ Hotkey Manager")
        self.setModal(True)
        self.setMinimumWidth(750)
        self.setMinimumHeight(550)
        self.hotkeys = []
        self.init_ui()
        self.refresh_hotkeys()

    def init_ui(self):
        """Initialize the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title = SubtitleLabel("Global Hotkeys")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        layout.addWidget(title)

        desc = BodyLabel("Manage global hotkeys for GTT automation. Hotkeys persist across sessions.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8b949e; font-size: 13px;")
        layout.addWidget(desc)

        # Add hotkey section
        add_layout = QHBoxLayout()
        add_layout.addWidget(BodyLabel("New Hotkey:"))
        self.new_hotkey_input = LineEdit()
        self.new_hotkey_input.setPlaceholderText("e.g., ctrl+alt+t")
        self.new_hotkey_input.setMaximumWidth(180)
        self.new_hotkey_input.setMinimumHeight(35)
        add_layout.addWidget(self.new_hotkey_input)

        add_layout.addWidget(BodyLabel("→"))

        self.new_hotkey_cmd_input = LineEdit()
        self.new_hotkey_cmd_input.setPlaceholderText("e.g., key ctrl+c or type Hello World")
        self.new_hotkey_cmd_input.setMinimumHeight(35)
        add_layout.addWidget(self.new_hotkey_cmd_input)

        self.add_hotkey_btn = PrimaryPushButton("Add Hotkey")
        self.add_hotkey_btn.setMinimumHeight(35)
        self.add_hotkey_btn.clicked.connect(self.add_hotkey)
        add_layout.addWidget(self.add_hotkey_btn)
        layout.addLayout(add_layout)

        # Hotkey list
        list_title = StrongBodyLabel("Registered Hotkeys")
        layout.addWidget(list_title)

        self.hotkey_list_widget = QListWidget()
        self.hotkey_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1a1f26;
                border: 1px solid #30363d;
                border-radius: 8px;
                color: #e6edf3;
                font-size: 13px;
            }
            QListWidget::item { padding: 10px; border-radius: 4px; }
            QListWidget::item:selected { background-color: #1f6feb; }
        """)
        self.hotkey_list_widget.setMinimumHeight(350)
        layout.addWidget(self.hotkey_list_widget)

        # Actions
        btn_layout = QHBoxLayout()
        self.remove_hotkey_btn = PushButton("Remove Selected")
        self.remove_hotkey_btn.setMinimumHeight(35)
        self.remove_hotkey_btn.clicked.connect(self.remove_selected_hotkey)
        btn_layout.addWidget(self.remove_hotkey_btn)

        self.clear_all_btn = PushButton("Clear All")
        self.clear_all_btn.setMinimumHeight(35)
        self.clear_all_btn.setStyleSheet("color: #f85149;")
        self.clear_all_btn.clicked.connect(self.clear_all_hotkeys)
        btn_layout.addWidget(self.clear_all_btn)

        btn_layout.addStretch()
        self.refresh_btn = PushButton("🔄 Refresh")
        self.refresh_btn.setMinimumHeight(35)
        self.refresh_btn.clicked.connect(self.refresh_hotkeys)
        btn_layout.addWidget(self.refresh_btn)

        self.close_btn = PushButton("Close")
        self.close_btn.setMinimumHeight(35)
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

    def refresh_hotkeys(self):
        """Refresh hotkey list from gtt"""
        self.hotkey_list_widget.clear()
        self.hotkeys = []
        try:
            result = subprocess.run(["gtt", "--list-hotkeys"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    for line in output.split('\n'):
                        if line.strip():
                            self.hotkeys.append(line.strip())
                            self.hotkey_list_widget.addItem(QListWidgetItem(line.strip()))
                else:
                    item = QListWidgetItem("No hotkeys registered")
                    item.setStyleSheet("color: #8b949e; font-style: italic;")
                    self.hotkey_list_widget.addItem(item)
            else:
                InfoBar.warning("Error", f"Failed to list hotkeys: {result.stderr}", parent=self, duration=3000)
        except Exception as e:
            InfoBar.error("Error", str(e), parent=self, duration=3000)

    def add_hotkey(self):
        """Add a new hotkey"""
        key_combo = self.new_hotkey_input.text().strip()
        command = self.new_hotkey_cmd_input.text().strip()
        if not key_combo or not command:
            InfoBar.warning("Invalid Input", "Please enter both key combination and command", parent=self, duration=3000)
            return
        try:
            result = subprocess.run(["gtt", "--hotkey-input", f"{key_combo},{command}"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                InfoBar.success("Hotkey Added", f"Registered {key_combo} → {command}", parent=self, duration=2000)
                self.new_hotkey_input.clear()
                self.new_hotkey_cmd_input.clear()
                self.refresh_hotkeys()
            else:
                InfoBar.error("Error", f"Failed to add hotkey: {result.stderr}", parent=self, duration=4000)
        except Exception as e:
            InfoBar.error("Error", str(e), parent=self, duration=4000)

    def remove_selected_hotkey(self):
        """Remove selected hotkey"""
        current_item = self.hotkey_list_widget.currentItem()
        if not current_item:
            InfoBar.warning("No Selection", "Please select a hotkey to remove", parent=self, duration=2000)
            return
        InfoBar.info("Not Implemented", "Hotkey removal requires gtt API update", parent=self, duration=3000)

    def clear_all_hotkeys(self):
        """Clear all hotkeys"""
        msg_box = MessageBox("Clear All Hotkeys?", "This will remove all registered hotkeys. This action cannot be undone.", self)
        msg_box.yesButton.setText("Clear All")
        msg_box.cancelButton.setText("Cancel")
        if msg_box.exec():
            try:
                result = subprocess.run(["gtt", "--clear-hotkeys"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    InfoBar.success("Cleared", "All hotkeys have been removed", parent=self, duration=2000)
                    self.refresh_hotkeys()
                else:
                    InfoBar.error("Error", f"Failed to clear hotkeys: {result.stderr}", parent=self, duration=4000)
            except Exception as e:
                InfoBar.error("Error", str(e), parent=self, duration=4000)


# ============================================================================
# Console Output Panel - Reusable widget
# ============================================================================

class ConsoleOutputPanel(QWidget):
    """Console output panel with filtering and search capabilities"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize console panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        # Filter toggles
        self.filter_info = ToggleButton("INFO")
        self.filter_info.setChecked(True)
        self.filter_info.setMinimumHeight(32)
        toolbar.addWidget(self.filter_info)
        
        self.filter_error = ToggleButton("ERROR")
        self.filter_error.setChecked(True)
        self.filter_error.setMinimumHeight(32)
        toolbar.addWidget(self.filter_error)
        
        self.filter_success = ToggleButton("SUCCESS")
        self.filter_success.setChecked(True)
        self.filter_success.setMinimumHeight(32)
        toolbar.addWidget(self.filter_success)
        
        self.filter_command = ToggleButton("COMMAND")
        self.filter_command.setChecked(True)
        self.filter_command.setMinimumHeight(32)
        toolbar.addWidget(self.filter_command)
        
        toolbar.addStretch()
        
        # Search
        self.search_box = SearchLineEdit()
        self.search_box.setPlaceholderText("Search console...")
        self.search_box.setMaximumWidth(200)
        self.search_box.setMinimumHeight(32)
        self.search_box.textChanged.connect(self.filter_console)
        toolbar.addWidget(self.search_box)
        
        # Auto-scroll
        self.auto_scroll_switch = SwitchButton()
        self.auto_scroll_switch.setChecked(True)
        self.auto_scroll_switch.setOnText("Auto-scroll")
        self.auto_scroll_switch.setOffText("Auto-scroll")
        self.auto_scroll_switch.setMinimumWidth(100)
        toolbar.addWidget(self.auto_scroll_switch)
        
        # Actions
        self.clear_btn = TransparentToolButton(FluentIcon.DELETE)
        self.clear_btn.setToolTip("Clear console (Ctrl+L)")
        self.clear_btn.setMinimumHeight(32)
        self.clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(self.clear_btn)
        
        self.copy_btn = TransparentToolButton(FluentIcon.COPY)
        self.copy_btn.setToolTip("Copy all")
        self.copy_btn.setMinimumHeight(32)
        self.copy_btn.clicked.connect(self.copy_all)
        toolbar.addWidget(self.copy_btn)
        
        self.save_btn = TransparentToolButton(FluentIcon.SAVE)
        self.save_btn.setToolTip("Save to file")
        self.save_btn.setMinimumHeight(32)
        self.save_btn.clicked.connect(self.save_to_file)
        toolbar.addWidget(self.save_btn)
        
        layout.addLayout(toolbar)
        
        # Console output
        self.console_output = TextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("""
            TextEdit {
                background-color: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 10px;
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
                font-size: 12px;
                line-height: 1.5;
            }
            TextEdit:focus { border-color: #1f6feb; }
        """)
        layout.addWidget(self.console_output)
        
        # Status bar
        status_bar = QHBoxLayout()
        self.line_count_label = CaptionLabel("0 lines")
        self.line_count_label.setStyleSheet("color: #8b949e;")
        status_bar.addWidget(self.line_count_label)
        status_bar.addStretch()
        self.bus_status_label = CaptionLabel("📡 Bus: Offline")
        self.bus_status_label.setStyleSheet("color: #8b949e;")
        status_bar.addWidget(self.bus_status_label)
        layout.addLayout(status_bar)
        
    def append(self, message: str, msg_type: str = "info"):
        """Append message to console"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icons = {"command": "▶", "output": "  ", "error": "✗", "info": "ℹ", "success": "✓"}
        icon = icons.get(msg_type, "ℹ")
        formatted = f"[{timestamp}] {icon} {message}"
        self.console_output.append(formatted)
        
        if self.auto_scroll_switch.isChecked():
            scrollbar = self.console_output.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
        self._update_line_count()
        
    def clear(self):
        """Clear console"""
        self.console_output.clear()
        self._update_line_count()
        InfoBar.info("Console Cleared", "All output has been cleared", parent=self.parent(), duration=1500)
        
    def copy_all(self):
        """Copy all console content"""
        from PySide6.QtGui import QClipboard
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.console_output.toPlainText())
        InfoBar.success("Copied", "Console content copied to clipboard", parent=self.parent(), duration=1500)
        
    def save_to_file(self):
        """Save console to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Console Output", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.console_output.toPlainText())
                InfoBar.success("Saved", f"Console saved to {file_path.split('/')[-1]}", parent=self.parent(), duration=2000)
            except Exception as e:
                InfoBar.error("Error", str(e), parent=self.parent(), duration=3000)
                
    def filter_console(self):
        """Filter console based on search text"""
        # Simple implementation - could be enhanced with highlighting
        pass
        
    def _update_line_count(self):
        """Update line count label"""
        lines = self.console_output.toPlainText().split('\n')
        self.line_count_label.setText(f"{len(lines)} lines")
        
    def set_bus_status(self, connected: bool):
        """Update bus status indicator"""
        self.bus_status_label.setText(f"📡 Bus: {'Connected' if connected else 'Offline'}")
        self.bus_status_label.setStyleSheet(f"color: {'#3fb950' if connected else '#8b949e'};")


# ============================================================================
# Script Builder Panel - Reusable widget
# ============================================================================

class ScriptBuilderPanel(QWidget):
    """Script builder panel with command palette and script list"""
    
    command_added = Signal(dict)  # Emits command data when added
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.script_commands = []
        self.window_list = []
        self.init_ui()
        
    def init_ui(self):
        """Initialize script builder UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Title
        title = SubtitleLabel("Script Builder")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title)
        
        # Command palette
        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(BodyLabel("Command:"))
        self.command_type_combo = ComboBox()
        self.command_type_combo.setMinimumHeight(40)
        self.command_type_combo.addItems(self._get_all_commands())
        cmd_layout.addWidget(self.command_type_combo)
        
        # AI button
        self.ai_btn = TransparentToolButton(FluentIcon.ROBOT)
        self.ai_btn.setToolTip("✨ AI Command Generator")
        self.ai_btn.setMinimumHeight(40)
        self.ai_btn.clicked.connect(self.show_ai_dialog)
        cmd_layout.addWidget(self.ai_btn)
        layout.addLayout(cmd_layout)
        
        # Parameters area
        self.params_scroll = QScrollArea()
        self.params_scroll.setWidgetResizable(True)
        self.params_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.params_scroll.setMaximumHeight(200)
        self.params_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #1a1f26;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        
        self.params_widget = QWidget()
        self.params_layout = QVBoxLayout(self.params_widget)
        self.params_layout.setContentsMargins(10, 10, 10, 10)
        self.params_layout.setSpacing(8)
        self.params_scroll.setWidget(self.params_widget)
        layout.addWidget(self.params_scroll)
        
        # Add button
        self.add_command_btn = PrimaryPushButton("Add Command to Script")
        self.add_command_btn.setMinimumHeight(40)
        self.add_command_btn.clicked.connect(self.add_command)
        layout.addWidget(self.add_command_btn)
        
        # Script list
        list_title = StrongBodyLabel("Script Commands")
        layout.addWidget(list_title)
        
        self.script_list = QListWidget()
        self.script_list.setStyleSheet("""
            QListWidget {
                background-color: #1a1f26;
                border: 1px solid #30363d;
                border-radius: 8px;
                color: #e6edf3;
                font-size: 13px;
            }
            QListWidget::item { padding: 10px; border-radius: 4px; }
            QListWidget::item:selected { background-color: #1f6feb; }
        """)
        self.script_list.setMinimumHeight(300)
        self.script_list.itemDoubleClicked.connect(self.remove_selected_command)
        layout.addWidget(self.script_list)
        
        # Script controls
        controls = QHBoxLayout()
        self.remove_btn = PushButton("Remove Selected")
        self.remove_btn.setMinimumHeight(35)
        self.remove_btn.clicked.connect(self.remove_selected_command)
        controls.addWidget(self.remove_btn)
        
        self.clear_btn = PushButton("Clear All")
        self.clear_btn.setMinimumHeight(35)
        self.clear_btn.clicked.connect(self.clear_script)
        controls.addWidget(self.clear_btn)
        
        self.export_btn = PushButton("📤 Export")
        self.export_btn.setMinimumHeight(35)
        self.export_btn.clicked.connect(self.export_script)
        controls.addWidget(self.export_btn)
        
        self.import_btn = PushButton("📥 Import")
        self.import_btn.setMinimumHeight(35)
        self.import_btn.clicked.connect(self.import_script)
        controls.addWidget(self.import_btn)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        # Dry-run toggle
        dry_run = QHBoxLayout()
        dry_run.addWidget(BodyLabel("Dry-run mode:"))
        self.dry_run_switch = SwitchButton()
        self.dry_run_switch.setChecked(False)
        self.dry_run_switch.setOnText("Preview only")
        self.dry_run_switch.setOffText("Execute")
        dry_run.addWidget(self.dry_run_switch)
        dry_run.addStretch()
        layout.addLayout(dry_run)
        
        # Execute button
        self.execute_btn = PrimaryPushButton("▶ Execute Script")
        self.execute_btn.setMinimumHeight(45)
        self.execute_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.execute_btn.clicked.connect(self.execute_script)
        layout.addWidget(self.execute_btn)
        
        # Progress
        self.progress_container = QWidget()
        self.progress_container.setStyleSheet("background-color: #1a1f26; border-radius: 8px; padding: 10px;")
        progress_layout = QVBoxLayout(self.progress_container)
        self.progress_ring = IndeterminateProgressRing()
        self.progress_ring.setFixedSize(32, 32)
        self.progress_ring.setVisible(False)
        progress_layout.addWidget(self.progress_ring, alignment=Qt.AlignmentFlag.AlignCenter)
        self.progress_label = BodyLabel("Executing...")
        self.progress_label.setStyleSheet("color: #8b949e;")
        self.progress_label.setVisible(False)
        progress_layout.addWidget(self.progress_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.progress_container.setVisible(False)
        layout.addWidget(self.progress_container)
        
        # Connect signals
        self.command_type_combo.currentIndexChanged.connect(self.on_command_changed)
        
    def _get_all_commands(self) -> List[str]:
        """Get all available GTT commands"""
        return [
            # Window
            "Focus Window", "Close Window", "Maximize Window", "Minimize Window",
            "Unmaximize Window", "Unminimize Window", "Activate Window",
            "Move Window", "Resize Window",
            # Apps
            "Launch App",
            # Input
            "Type Text", "Send Keys", "Mouse Click", "Mouse Move",
            # Clipboard
            "Get Clipboard", "Set Clipboard", "Paste Clipboard",
            # Screenshot/OCR
            "Screenshot", "OCR Active Window", "OCR File",
            # Layout
            "Save Layout", "Restore Layout", "Snap Window",
            # Hotkeys
            "Register Hotkey Script", "Register Hotkey Input",
            "List Hotkeys", "Clear Hotkeys",
            # Macros
            "Add Macro", "Remove Macro", "List Macros",
            # GNOME
            "GNOME Eval", "GNOME Notify", "GNOME Open File",
            # Vision
            "Vision Scan", "Vision Map", "Vision Click",
            # Subscriptions
            "Subscribe Events",
            # Utility
            "Wait", "Get Active Window", "List Windows",
            # TermPipe
            "TermPipe Shell Command",
            # AI
            "✨ Command (AI-Powered)",
        ]
        
    def on_command_changed(self, index):
        """Handle command type change"""
        # Clear existing params
        while self.params_layout.count():
            child = self.params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        cmd_type = self.command_type_combo.currentText()
        self._add_params_for_command(cmd_type)
        
    def _add_params_for_command(self, cmd_type: str):
        """Add parameter inputs for selected command"""
        # Window operations
        if cmd_type in ["Focus Window", "Close Window", "Maximize Window", "Minimize Window",
                        "Unmaximize Window", "Unminimize Window", "Activate Window"]:
            self.params_layout.addWidget(BodyLabel("Select Window:"))
            self.param_window_combo = ComboBox()
            self.param_window_combo.setMinimumHeight(35)
            for window in self.window_list:
                title = window.get("title", "Untitled")[:50]
                self.param_window_combo.addItem(title, userData=window.get("id"))
            self.params_layout.addWidget(self.param_window_combo)
            
        elif cmd_type == "Move Window":
            self._add_window_selector()
            coords = QHBoxLayout()
            coords.addWidget(BodyLabel("X:"))
            self.param_move_x = LineEdit()
            self.param_move_x.setPlaceholderText("e.g., 100 or 0.5")
            self.param_move_x.setMinimumHeight(35)
            coords.addWidget(self.param_move_x)
            coords.addWidget(BodyLabel("Y:"))
            self.param_move_y = LineEdit()
            self.param_move_y.setPlaceholderText("e.g., 200 or 0.3")
            self.param_move_y.setMinimumHeight(35)
            coords.addWidget(self.param_move_y)
            self.params_layout.addLayout(coords)
            
        elif cmd_type == "Resize Window":
            self._add_window_selector()
            dims = QHBoxLayout()
            dims.addWidget(BodyLabel("Width:"))
            self.param_resize_w = LineEdit()
            self.param_resize_w.setPlaceholderText("e.g., 800 or 0.5")
            self.param_resize_w.setMinimumHeight(35)
            dims.addWidget(self.param_resize_w)
            dims.addWidget(BodyLabel("Height:"))
            self.param_resize_h = LineEdit()
            self.param_resize_h.setPlaceholderText("e.g., 600 or 0.7")
            self.param_resize_h.setMinimumHeight(35)
            dims.addWidget(self.param_resize_h)
            self.params_layout.addLayout(dims)
            
        elif cmd_type == "Launch App":
            self.params_layout.addWidget(BodyLabel("App Name:"))
            self.param_app_name = LineEdit()
            self.param_app_name.setPlaceholderText("e.g., Firefox, Visual Studio Code")
            self.param_app_name.setMinimumHeight(35)
            self.params_layout.addWidget(self.param_app_name)
            
        elif cmd_type == "Type Text":
            self.params_layout.addWidget(BodyLabel("Text:"))
            self.param_text = LineEdit()
            self.param_text.setPlaceholderText("Enter text to type")
            self.param_text.setMinimumHeight(35)
            self.params_layout.addWidget(self.param_text)
            
        elif cmd_type == "Send Keys":
            self.params_layout.addWidget(BodyLabel("Key Combination:"))
            self.param_keys = LineEdit()
            self.param_keys.setPlaceholderText("e.g., ctrl+c, super+Enter")
            self.param_keys.setMinimumHeight(35)
            self.params_layout.addWidget(self.param_keys)
            
        elif cmd_type == "Screenshot":
            self.params_layout.addWidget(BodyLabel("Save Path:"))
            self.param_screenshot_path = LineEdit()
            self.param_screenshot_path.setText("/tmp/screenshot.png")
            self.param_screenshot_path.setMinimumHeight(35)
            self.params_layout.addWidget(self.param_screenshot_path)
            
        elif cmd_type == "Wait":
            self.params_layout.addWidget(BodyLabel("Duration (ms):"))
            self.param_wait = QSpinBox()
            self.param_wait.setMaximum(60000)
            self.param_wait.setValue(1000)
            self.param_wait.setMinimumHeight(35)
            self.params_layout.addWidget(self.param_wait)
            
        elif cmd_type == "TermPipe Shell Command":
            self.params_layout.addWidget(BodyLabel("Shell Command:"))
            self.param_termpipe = LineEdit()
            self.param_termpipe.setPlaceholderText("e.g., ls -la ~/projects")
            self.param_termpipe.setMinimumHeight(35)
            self.params_layout.addWidget(self.param_termpipe)
            info = CaptionLabel("💡 Powered by TermPipe (MiniMax-M2.1)")
            info.setStyleSheet("color: #4A90E2;")
            self.params_layout.addWidget(info)
            
        # Add more command params as needed...
        
    def _add_window_selector(self):
        """Add window selector to params"""
        self.params_layout.addWidget(BodyLabel("Select Window:"))
        self.param_window_combo = ComboBox()
        self.param_window_combo.setMinimumHeight(35)
        for window in self.window_list:
            title = window.get("title", "Untitled")[:50]
            self.param_window_combo.addItem(title, userData=window.get("id"))
        self.params_layout.addWidget(self.param_window_combo)
        
    def show_ai_dialog(self):
        """Show AI command generator"""
        self.command_type_combo.setCurrentIndex(0)
        dialog = AICommandDialog(self.parent())
        dialog.command_generated.connect(self.add_generated_command)
        dialog.show()
        
    def add_generated_command(self, cmd_data: dict):
        """Add AI-generated command"""
        self.script_commands.append(cmd_data)
        self._add_to_list(cmd_data)
        
    def add_command(self):
        """Add current command to script"""
        cmd_type = self.command_type_combo.currentText()
        cmd_data = {"type": cmd_type, "params": {}}
        
        # Collect params (simplified - expand for all command types)
        if hasattr(self, 'param_window_combo'):
            cmd_data["params"]["window_id"] = self.param_window_combo.currentData()
        if hasattr(self, 'param_app_name'):
            cmd_data["params"]["app_name"] = self.param_app_name.text()
        if hasattr(self, 'param_text'):
            cmd_data["params"]["text"] = self.param_text.text()
        if hasattr(self, 'param_keys'):
            cmd_data["params"]["keys"] = self.param_keys.text()
        if hasattr(self, 'param_move_x'):
            cmd_data["params"]["x"] = self.param_move_x.text()
        if hasattr(self, 'param_move_y'):
            cmd_data["params"]["y"] = self.param_move_y.text()
        if hasattr(self, 'param_resize_w'):
            cmd_data["params"]["w"] = self.param_resize_w.text()
        if hasattr(self, 'param_resize_h'):
            cmd_data["params"]["h"] = self.param_resize_h.text()
        if hasattr(self, 'param_screenshot_path'):
            cmd_data["params"]["path"] = self.param_screenshot_path.text()
        if hasattr(self, 'param_wait'):
            cmd_data["params"]["duration"] = self.param_wait.value()
        if hasattr(self, 'param_termpipe'):
            cmd_data["params"]["command"] = self.param_termpipe.text()
            
        self.script_commands.append(cmd_data)
        self._add_to_list(cmd_data)
        InfoBar.success("Command Added", f"Added {cmd_type}", parent=self.parent(), duration=1500)
        
    def _add_to_list(self, cmd_data: dict):
        """Add command to list widget"""
        cmd_type = cmd_data["type"]
        params = cmd_data.get("params", {})
        if params:
            params_str = ", ".join(f"{k}={v}" for k, v in params.items())
            item_text = f"{cmd_type} ({params_str})"
        else:
            item_text = cmd_type
            
        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, len(self.script_commands) - 1)
        self.script_list.addItem(item)
        
    def remove_selected_command(self):
        """Remove selected command"""
        current = self.script_list.currentItem()
        if current:
            index = current.data(Qt.UserRole)
            if 0 <= index < len(self.script_commands):
                self.script_commands.pop(index)
                self.script_list.takeItem(self.script_list.row(current))
                # Re-index
                for i in range(self.script_list.count()):
                    self.script_list.item(i).setData(Qt.UserRole, i)
                    
    def clear_script(self):
        """Clear all commands"""
        self.script_commands = []
        self.script_list.clear()
        InfoBar.info("Script Cleared", "All commands removed", parent=self.parent(), duration=1500)
        
    def export_script(self):
        """Export script to JSON"""
        if not self.script_commands:
            InfoBar.warning("Empty Script", "No commands to export", parent=self.parent(), duration=2000)
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save GTT Script", "", "GTT Script Files (*.gtt.json);;JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                export_data = {
                    "version": "1.0",
                    "name": file_path.split("/")[-1].replace(".gtt.json", "").replace(".json", ""),
                    "commands": self.script_commands,
                    "command_count": len(self.script_commands)
                }
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                InfoBar.success("Export Successful", f"Saved {len(self.script_commands)} commands", parent=self.parent(), duration=3000)
            except Exception as e:
                InfoBar.error("Export Failed", str(e), parent=self.parent(), duration=4000)
                
    def import_script(self):
        """Import script from JSON"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load GTT Script", "", "GTT Script Files (*.gtt.json);;JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
                if "commands" not in import_data:
                    raise ValueError("Invalid format")
                self.script_commands = []
                self.script_list.clear()
                for cmd in import_data["commands"]:
                    self.script_commands.append(cmd)
                    self._add_to_list(cmd)
                InfoBar.success("Import Successful", f"Loaded {len(self.script_commands)} commands", parent=self.parent(), duration=3000)
            except Exception as e:
                InfoBar.error("Import Failed", str(e), parent=self.parent(), duration=4000)
                
    def execute_script(self):
        """Execute or preview script"""
        if not self.script_commands:
            InfoBar.warning("Empty Script", "Add commands first", parent=self.parent(), duration=2000)
            return
        # Signal parent to execute
        if hasattr(self.parent(), 'on_execute_script'):
            self.parent().on_execute_script(self.script_commands, self.dry_run_switch.isChecked())


# ============================================================================
# Main GTT Page - Container assembling all components
# ============================================================================

class GTTPage(QWidget):
    """GTT automation page with window management, macros, and NLP integration"""

    def __init__(self, main_window):
        super().__init__()
        self.setObjectName("GTTPage")
        self.main_window = main_window
        self.cliproxy_url = "http://localhost:7599"
        
        # State
        self.script_commands = []
        self.window_list = []
        self.gtt_running = False
        self.startup_thread = None
        
        # Bus client
        self.bus = BusClient()
        
        # References
        self.settings_manager = main_window.get_settings_manager()
        self.voice_processor = main_window.get_voice_processor()
        
        self.init_ui()
        self.connect_signals()
        self.check_gtt_status()

    def init_ui(self):
        """Initialize the main UI layout"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left sidebar (280px fixed)
        left_sidebar = self._create_left_sidebar()
        left_sidebar.setFixedWidth(280)
        main_layout.addWidget(left_sidebar)

        # Center content area (tabs)
        center_content = self._create_center_content()
        main_layout.addWidget(center_content)

        # Right sidebar (320px fixed)
        right_sidebar = self._create_right_sidebar()
        right_sidebar.setFixedWidth(320)
        main_layout.addWidget(right_sidebar)

    def _create_left_sidebar(self) -> QWidget:
        """Create left sidebar with daemon status, windows, macros"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 10, 15)
        layout.setSpacing(12)

        # Daemon status
        status_title = SubtitleLabel("GTT Daemon")
        status_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(status_title)

        status_card = CardWidget()
        status_card.setStyleSheet("""
            CardWidget {
                background-color: #1a1f26;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        status_layout = QHBoxLayout(status_card)
        self.status_indicator = IndeterminateProgressRing()
        self.status_indicator.setFixedSize(20, 20)
        status_layout.addWidget(self.status_indicator)
        self.status_label = BodyLabel("Not Running")
        self.status_label.setStyleSheet("color: #8b949e;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addWidget(status_card)

        self.start_gtt_btn = PrimaryPushButton("▶ Start GTT")
        self.start_gtt_btn.setMinimumHeight(38)
        self.start_gtt_btn.clicked.connect(self.start_gtt_daemon)
        layout.addWidget(self.start_gtt_btn)

        self.startup_progress = ProgressBar()
        self.startup_progress.setVisible(False)
        layout.addWidget(self.startup_progress)

        layout.addSpacing(10)

        # Window list
        window_title = SubtitleLabel("Windows")
        window_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(window_title)

        refresh_btn = TransparentToolButton(FluentIcon.SYNC)
        refresh_btn.setToolTip("Refresh window list")
        refresh_btn.setMinimumHeight(32)
        refresh_btn.clicked.connect(self.refresh_windows)
        layout.addWidget(refresh_btn)

        self.window_list_widget = QListWidget()
        self.window_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1a1f26;
                border: 1px solid #30363d;
                border-radius: 8px;
                color: #e6edf3;
                font-size: 12px;
            }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background-color: #238636; }
        """)
        self.window_list_widget.setMaximumHeight(180)
        layout.addWidget(self.window_list_widget)

        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)
        actions_layout = QGridLayout(actions_group)
        actions_layout.setSpacing(6)
        
        self.focus_window_btn = PushButton("Focus")
        self.focus_window_btn.setMinimumHeight(32)
        self.focus_window_btn.clicked.connect(self.focus_selected_window)
        actions_layout.addWidget(self.focus_window_btn, 0, 0)
        
        self.close_window_btn = PushButton("Close")
        self.close_window_btn.setMinimumHeight(32)
        self.close_window_btn.clicked.connect(self.close_selected_window)
        actions_layout.addWidget(self.close_window_btn, 0, 1)
        
        self.minimize_window_btn = PushButton("Minimize")
        self.minimize_window_btn.setMinimumHeight(32)
        self.minimize_window_btn.clicked.connect(self.minimize_selected_window)
        actions_layout.addWidget(self.minimize_window_btn, 1, 0)
        
        self.maximize_window_btn = PushButton("Maximize")
        self.maximize_window_btn.setMinimumHeight(32)
        self.maximize_window_btn.clicked.connect(self.maximize_selected_window)
        actions_layout.addWidget(self.maximize_window_btn, 1, 1)
        
        self.unmaximize_window_btn = PushButton("Restore")
        self.unmaximize_window_btn.setMinimumHeight(32)
        self.unmaximize_window_btn.clicked.connect(self.unmaximize_selected_window)
        actions_layout.addWidget(self.unmaximize_window_btn, 2, 0)
        actions_layout.setColumnStretch(2, 1)
        layout.addWidget(actions_group)

        layout.addSpacing(10)

        # Hotkey manager
        hotkey_title = SubtitleLabel("⌨️ Hotkeys")
        hotkey_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(hotkey_title)

        self.hotkey_manager_btn = PrimaryPushButton("Manage Hotkeys")
        self.hotkey_manager_btn.setMinimumHeight(38)
        self.hotkey_manager_btn.clicked.connect(self.open_hotkey_manager)
        layout.addWidget(self.hotkey_manager_btn)

        layout.addSpacing(10)

        # Macros
        macros_title = SubtitleLabel("Macros")
        macros_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(macros_title)

        macros_scroll = QScrollArea()
        macros_scroll.setWidgetResizable(True)
        macros_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        macros_widget = QWidget()
        macros_layout = QGridLayout(macros_widget)
        macros_layout.setSpacing(6)
        
        macros = [
            ("Focus Hyper", "focus_hyper"),
            ("Focus VS Code", "focus_vscode"),
            ("Focus Browser", "focus_browser"),
            ("Type Hello", "type_hello"),
            ("Copy/Paste", "copy_paste"),
            ("New Terminal", "new_terminal"),
            ("Screenshot", "screenshot"),
            ("Maximize", "maximize_window"),
            ("OCR Active", "ocr_active"),
            ("Clipboard", "clipboard_get"),
        ]
        
        for i, (name, macro_id) in enumerate(macros):
            btn = PushButton(name)
            btn.setMinimumHeight(32)
            btn.clicked.connect(lambda checked, mid=macro_id: self.execute_macro(mid))
            macros_layout.addWidget(btn, i // 2, i % 2)
            
        macros_layout.setRowStretch((len(macros) // 2) + 1, 1)
        macros_scroll.setWidget(macros_widget)
        layout.addWidget(macros_scroll)

        layout.addStretch()
        return widget

    def _create_center_content(self) -> QWidget:
        """Create center tab widget"""
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: transparent;
            }
            QTabBar::tab {
                background-color: #1a1f26;
                color: #8b949e;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background-color: #238636;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #21262d;
            }
        """)
        tabs.setMinimumHeight(50)

        # Tab 1: Script Builder
        script_tab = QWidget()
        script_layout = QVBoxLayout(script_tab)
        script_layout.setContentsMargins(15, 15, 15, 15)
        script_layout.setSpacing(12)
        
        self.script_builder = ScriptBuilderPanel(self)
        self.script_builder.window_list = self.window_list
        script_layout.addWidget(self.script_builder)
        tabs.addTab(script_tab, "📝 Script Builder")

        # Tab 2: Console
        console_tab = QWidget()
        console_layout = QVBoxLayout(console_tab)
        console_layout.setContentsMargins(15, 15, 15, 15)
        console_layout.setSpacing(12)
        
        self.console_panel = ConsoleOutputPanel(self)
        console_layout.addWidget(self.console_panel)
        tabs.addTab(console_tab, "📋 Console Output")

        # Tab 3: Hotkey Manager (integrated)
        hotkey_tab = QWidget()
        hotkey_layout = QVBoxLayout(hotkey_tab)
        hotkey_layout.setContentsMargins(15, 15, 15, 15)
        hotkey_layout.setSpacing(12)
        
        hotkey_info = BodyLabel("Use the Hotkey Manager button in the left sidebar to manage hotkeys.")
        hotkey_info.setStyleSheet("color: #8b949e; font-size: 13px;")
        hotkey_layout.addWidget(hotkey_info)
        
        self.hotkey_preview = QListWidget()
        self.hotkey_preview.setStyleSheet("""
            QListWidget {
                background-color: #1a1f26;
                border: 1px solid #30363d;
                border-radius: 8px;
                color: #e6edf3;
                font-size: 13px;
            }
        """)
        hotkey_layout.addWidget(self.hotkey_preview)
        tabs.addTab(hotkey_tab, "⌨️ Hotkey Manager")

        return tabs

    def _create_right_sidebar(self) -> QWidget:
        """Create right sidebar with NLP, voice control, history"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 15, 15, 15)
        layout.setSpacing(12)

        # NLP bar
        nlp_title = SubtitleLabel("💡 NLP Command")
        nlp_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(nlp_title)

        badge = CaptionLabel("Powered by OmniProxy • MiniMax-M2.1 / Qwen3-Coder")
        badge.setStyleSheet("color: #4A90E2; font-weight: bold;")
        layout.addWidget(badge)

        self.nlp_input = LineEdit()
        self.nlp_input.setPlaceholderText("e.g., 'focus firefox and open new tab'")
        self.nlp_input.setMinimumHeight(40)
        self.nlp_input.setStyleSheet("""
            LineEdit {
                padding: 10px;
                font-size: 14px;
                border: 2px solid #30363d;
                border-radius: 8px;
                background-color: #1a1f26;
                color: #e6edf3;
            }
            LineEdit:focus { border-color: #1f6feb; }
        """)
        self.nlp_input.returnPressed.connect(self.send_nlp_command)
        layout.addWidget(self.nlp_input)

        model_layout = QHBoxLayout()
        model_layout.addWidget(BodyLabel("Model:"))
        self.nlp_model_combo = ComboBox()
        self.nlp_model_combo.setMinimumHeight(35)
        self.nlp_model_combo.addItems([
            "qwen3-coder-plus (Fastest)",
            "minimax-m2.1 (Best for code)",
            "kimi-k2 (Deep reasoning)",
            "deepseek-v3.2 (Balanced)",
        ])
        model_layout.addWidget(self.nlp_model_combo)
        layout.addLayout(model_layout)

        self.send_nlp_btn = PrimaryPushButton("🚀 Send to GTT")
        self.send_nlp_btn.setMinimumHeight(40)
        self.send_nlp_btn.clicked.connect(self.send_nlp_command)
        layout.addWidget(self.send_nlp_btn)

        self.nlp_progress = IndeterminateProgressRing()
        self.nlp_progress.setFixedSize(24, 24)
        self.nlp_progress.setVisible(False)
        layout.addWidget(self.nlp_progress, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(10)

        # Voice control
        voice_title = SubtitleLabel("🎤 Voice Control")
        voice_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(voice_title)

        self.voice_input_btn = PrimaryPushButton("🎤 Start Voice Command")
        self.voice_input_btn.setMinimumHeight(45)
        self.voice_input_btn.clicked.connect(self.start_voice_command)
        layout.addWidget(self.voice_input_btn)

        self.voice_status_label = BodyLabel("Ready")
        self.voice_status_label.setStyleSheet("color: #8b949e;")
        layout.addWidget(self.voice_status_label)

        layout.addSpacing(10)

        # History
        history_title = StrongBodyLabel("📜 Command History")
        layout.addWidget(history_title)

        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget {
                background-color: #1a1f26;
                border: 1px solid #30363d;
                border-radius: 8px;
                color: #8b949e;
                font-size: 12px;
            }
        """)
        self.history_list.setMaximumHeight(120)
        layout.addWidget(self.history_list)

        layout.addStretch()
        return widget

    def connect_signals(self):
        """Connect UI signals"""
        self.bus_refresh_timer = QTimer()
        self.bus_refresh_timer.timeout.connect(self.refresh_bus_status)
        self.bus_refresh_timer.start(5000)

        self.bus_message_timer = QTimer()
        self.bus_message_timer.timeout.connect(self.check_bus_messages)
        self.bus_message_timer.start(100)

    def refresh_bus_status(self):
        """Refresh bus status"""
        self.bus._check_availability()
        if hasattr(self, 'console_panel'):
            self.console_panel.set_bus_status(self.bus.available)

    def check_bus_messages(self):
        """Check for bus messages"""
        if not self.bus.available:
            return
        # Handle incoming messages...

    def open_hotkey_manager(self):
        """Open hotkey manager dialog"""
        dialog = HotkeyManagerDialog(self)
        dialog.show()

    def on_execute_script(self, commands: List[dict], dry_run: bool):
        """Handle script execution from script builder"""
        if dry_run:
            self._preview_script(commands)
        else:
            self._execute_commands(commands)

    def _preview_script(self, commands: List[dict]):
        """Preview script without executing"""
        self.console_panel.append("=" * 60, "info")
        self.console_panel.append("📋 DRY-RUN MODE - Script Preview", "info")
        self.console_panel.append("=" * 60, "info")
        
        for i, cmd in enumerate(commands):
            params = cmd.get("params", {})
            if params:
                params_str = ", ".join(f"{k}={v}" for k, v in params.items())
                self.console_panel.append(f"[{i+1}] {cmd['type']}({params_str})", "command")
            else:
                self.console_panel.append(f"[{i+1}] {cmd['type']}", "command")
                
        self.console_panel.append("=" * 60, "info")
        InfoBar.info("Dry-run Complete", f"Previewed {len(commands)} commands", parent=self, duration=3000)

    def _execute_commands(self, commands: List[dict]):
        """Execute command list"""
        for i, cmd in enumerate(commands):
            self._execute_command_data(cmd)
            self.console_panel.append(f"[{i+1}/{len(commands)}] {cmd['type']}", "info")
        InfoBar.success("Script Complete", f"Executed {len(commands)} commands", parent=self, duration=2000)

    def _execute_command_data(self, cmd_data: dict):
        """Execute single command"""
        cmd_type = cmd_data["type"]
        params = cmd_data.get("params", {})
        
        # Window operations
        if cmd_type == "Focus Window" and params.get("window_id"):
            self.execute_gtt_command(["gtt", "--focus", str(params["window_id"])])
        elif cmd_type == "Close Window" and params.get("window_id"):
            self.execute_gtt_command(["gtt", "--close", str(params["window_id"])])
        elif cmd_type == "Launch App" and params.get("app_name"):
            self.execute_gtt_command(["gtt", "--launch", params["app_name"]])
        elif cmd_type == "Type Text" and params.get("text"):
            self.execute_gtt_command(["gtt", "--type", params["text"]])
        elif cmd_type == "Send Keys" and params.get("keys"):
            self.execute_gtt_command(["gtt", "--key", params["keys"]])
        elif cmd_type == "Screenshot" and params.get("path"):
            self.execute_gtt_command(["gtt", "--sc", params["path"]])
        elif cmd_type == "TermPipe Shell Command" and params.get("command"):
            self.execute_termpipe_command(params["command"])
        # Add more command handlers as needed...

    # Window management methods
    def refresh_windows(self):
        """Refresh window list"""
        try:
            result = subprocess.run(["gtt", "--list", "--format", "json"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.window_list = json.loads(result.stdout)
                self.window_list_widget.clear()
                for window in self.window_list:
                    title = window.get("title", "Untitled")[:50]
                    item = QListWidgetItem(title)
                    item.setData(Qt.UserRole, window.get("id"))
                    self.window_list_widget.addItem(item)
                # Update script builder
                if hasattr(self, 'script_builder'):
                    self.script_builder.window_list = self.window_list
                InfoBar.success("Windows Refreshed", f"Found {len(self.window_list)} windows", parent=self, duration=2000)
        except Exception as e:
            InfoBar.error("Error", str(e), parent=self, duration=3000)

    def get_selected_window_id(self) -> Optional[str]:
        """Get selected window ID"""
        current = self.window_list_widget.currentItem()
        return current.data(Qt.UserRole) if current else None

    def focus_selected_window(self):
        """Focus selected window"""
        window_id = self.get_selected_window_id()
        if window_id:
            self.execute_gtt_command(["gtt", "--focus", str(window_id)])
            self.console_panel.append(f"Focused window {window_id}", "success")
        else:
            InfoBar.warning("No Selection", "Please select a window", parent=self, duration=2000)

    def close_selected_window(self):
        """Close selected window"""
        window_id = self.get_selected_window_id()
        if window_id:
            self.execute_gtt_command(["gtt", "--close", str(window_id)])
            self.console_panel.append(f"Closed window {window_id}", "success")
            self.refresh_windows()
        else:
            InfoBar.warning("No Selection", "Please select a window", parent=self, duration=2000)

    def minimize_selected_window(self):
        """Minimize selected window"""
        window_id = self.get_selected_window_id()
        if window_id:
            self.execute_gtt_command(["gtt", "--minimize", str(window_id)])
            self.console_panel.append(f"Minimized window {window_id}", "success")

    def maximize_selected_window(self):
        """Maximize selected window"""
        window_id = self.get_selected_window_id()
        if window_id:
            self.execute_gtt_command(["gtt", "--maximize", str(window_id)])
            self.console_panel.append(f"Maximized window {window_id}", "success")

    def unmaximize_selected_window(self):
        """Unmaximize selected window"""
        window_id = self.get_selected_window_id()
        if window_id:
            self.execute_gtt_command(["gtt", "--unmaximize", str(window_id)])
            self.console_panel.append(f"Unmaximized window {window_id}", "success")

    # Macro execution
    def execute_macro(self, macro_id: str):
        """Execute pre-loaded macro"""
        macros = {
            "focus_hyper": ["gtt", "--launch", "Hyper"],
            "focus_vscode": ["gtt", "--focus", "Visual Studio Code"],
            "focus_browser": ["gtt", "--focus", "Firefox"],
            "type_hello": ["gtt", "--type", "Hello from GTT!"],
            "copy_paste": ["gtt", "--key", "ctrl+c", "--key", "ctrl+v"],
            "new_terminal": ["gtt", "--launch", "Hyper"],
            "screenshot": ["gtt", "--sc", "/tmp/screenshot.png"],
            "maximize_window": ["gtt", "--maximize", "active"],
            "ocr_active": ["gtt", "--ocr"],
            "clipboard_get": ["gtt", "--cb"],
        }
        if macro_id in macros:
            self.execute_gtt_command(macros[macro_id])
            self.console_panel.append(f"Executed macro: {macro_id}", "info")

    # NLP integration
    def send_nlp_command(self):
        """Send NLP command"""
        nlp_text = self.nlp_input.text().strip()
        if not nlp_text:
            InfoBar.warning("Empty Input", "Please enter a command", parent=self, duration=2000)
            return

        self.history_list.addItem(f"📝 {nlp_text}")
        self.nlp_progress.setVisible(True)

        try:
            response = requests.post(
                f"{self.cliproxy_url}/v1/chat/completions",
                json={
                    "model": "qwen3-coder-plus",
                    "messages": [
                        {"role": "system", "content": "You are a GTT command generator. Output ONLY the gtt command."},
                        {"role": "user", "content": nlp_text}
                    ]
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                gtt_cmd = data["choices"][0]["message"]["content"].strip()
                self.console_panel.append(f"NLP → {gtt_cmd}", "command")
                self.execute_parsed_command(gtt_cmd)
                InfoBar.success("NLP Success", f"Executed: {gtt_cmd}", parent=self, duration=2000)
            else:
                InfoBar.error("NLP Error", f"CLIProxy error: {response.status_code}", parent=self, duration=3000)
        except Exception as e:
            InfoBar.error("NLP Error", str(e), parent=self, duration=3000)
        finally:
            self.nlp_progress.setVisible(False)

    def execute_parsed_command(self, command: str):
        """Execute parsed GTT command"""
        if command.startswith("gtt "):
            command = command[4:]
        parts = command.split()
        if parts:
            self.execute_gtt_command(["gtt"] + parts)

    # Voice control
    def start_voice_command(self):
        """Start voice command"""
        self.voice_status_label.setText("Listening...")
        self.voice_status_label.setStyleSheet("color: #4A90E2;")
        self.voice_input_btn.setEnabled(False)

        try:
            success = self.voice_processor.start_recording()
            if success:
                InfoBar.info("Listening", "Speak your GTT command...", parent=self, duration=1000)
                QTimer.singleShot(5000, self.process_voice_command)
            else:
                self.reset_voice_state()
                InfoBar.error("Error", "Failed to start recording", parent=self, duration=2000)
        except Exception as e:
            self.reset_voice_state()
            InfoBar.error("Error", str(e), parent=self, duration=3000)

    def process_voice_command(self):
        """Process voice command"""
        try:
            audio_data = self.voice_processor.stop_recording()
            if audio_data:
                transcription = self.voice_processor.transcribe_audio(audio_data)
                if transcription:
                    self.voice_status_label.setText(f"Heard: '{transcription}'")
                    self.nlp_input.setText(transcription)
                    QTimer.singleShot(1000, self.send_nlp_command)
                else:
                    self.reset_voice_state()
                    InfoBar.warning("Transcription Failed", "Could not transcribe", parent=self, duration=2000)
            else:
                self.reset_voice_state()
                InfoBar.warning("No Audio", "No voice detected", parent=self, duration=2000)
        except Exception as e:
            self.reset_voice_state()
            InfoBar.error("Error", str(e), parent=self, duration=3000)

    def reset_voice_state(self):
        """Reset voice UI state"""
        self.voice_status_label.setText("Ready")
        self.voice_status_label.setStyleSheet("color: #8b949e;")
        self.voice_input_btn.setEnabled(True)

    # GTT daemon management
    def check_gtt_status(self):
        """Check GTT daemon status"""
        try:
            result = subprocess.run(["pgrep", "-f", "gttd"], capture_output=True, text=True, timeout=2)
            self.gtt_running = result.returncode == 0
            self.update_gtt_status_ui()
        except Exception:
            self.gtt_running = False
            self.update_gtt_status_ui()

    def update_gtt_status_ui(self):
        """Update status UI"""
        if self.gtt_running:
            self.status_label.setText("Running")
            self.status_label.setStyleSheet("color: #3fb950; font-weight: bold;")
            self.status_indicator.setVisible(False)
            self.start_gtt_btn.setText("⏹ Stop GTT")
            self.start_gtt_btn.setStyleSheet("PrimaryPushButton { background-color: #da3633; color: white; }")
        else:
            self.status_label.setText("Not Running")
            self.status_label.setStyleSheet("color: #8b949e;")
            self.status_indicator.setVisible(True)
            self.start_gtt_btn.setText("▶ Start GTT")
            self.start_gtt_btn.setStyleSheet("")

    def start_gtt_daemon(self):
        """Start/stop GTT daemon"""
        if self.gtt_running:
            self.stop_gtt_daemon()
            return

        self.startup_progress.setVisible(True)
        self.start_gtt_btn.setEnabled(False)

        self.startup_thread = GTTStartupThread()
        self.startup_thread.status_signal.connect(self.on_gtt_startup_status)
        self.startup_thread.completed_signal.connect(self.on_gtt_startup_complete)
        self.startup_thread.start()

    def stop_gtt_daemon(self):
        """Stop GTT daemon"""
        try:
            subprocess.run(["pkill", "-f", "gttd"], capture_output=True, timeout=2)
            subprocess.run(["pkill", "-f", "gtt-portal"], capture_output=True, timeout=2)
            self.gtt_running = False
            self.update_gtt_status_ui()
            self.console_panel.append("GTT daemon stopped", "info")
            InfoBar.info("GTT Stopped", "Daemon has been stopped", parent=self, duration=2000)
        except Exception as e:
            InfoBar.error("Error", str(e), parent=self, duration=3000)

    def on_gtt_startup_status(self, title: str, message: str):
        """Handle startup status"""
        self.status_label.setText(message)
        self.console_panel.append(f"[Startup] {message}", "info")

    def on_gtt_startup_complete(self, success: bool):
        """Handle startup complete"""
        self.startup_progress.setVisible(False)
        self.start_gtt_btn.setEnabled(True)
        if success:
            self.gtt_running = True
            self.update_gtt_status_ui()
            InfoBar.success("GTT Started", "Daemon is ready", parent=self, duration=3000)
            self.refresh_windows()
        else:
            InfoBar.error("Startup Failed", "Could not start daemon", parent=self, duration=3000)

    # TermPipe integration
    def execute_termpipe_command(self, command: str):
        """Execute TermPipe command"""
        try:
            self.console_panel.append(f"⚡ TermPipe: {command}", "command")
            result = subprocess.run(["termf", "--exec", command], capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                self.console_panel.append(result.stdout.strip(), "output")
            elif result.stderr:
                self.console_panel.append(f"Error: {result.stderr}", "error")
        except Exception as e:
            self.console_panel.append(f"Exception: {str(e)}", "error")

    # Utility methods
    def execute_gtt_command(self, cmd_list: List[str]):
        """Execute GTT command"""
        try:
            cmd_str = " ".join(cmd_list)
            self.console_panel.append(f"▶ {cmd_str}", "command")
            result = subprocess.run(cmd_list, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.console_panel.append(f"✗ {result.stderr}", "error")
            elif result.stdout:
                self.console_panel.append(f"✓ {result.stdout.strip()}", "output")
        except Exception as e:
            self.console_panel.append(f"✗ Exception: {str(e)}", "error")
