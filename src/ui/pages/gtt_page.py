"""
GTT (GreaterTouchTool) Page - Window automation and macro execution interface
Provides NLP-driven window management, script building, and voice-controlled automation
"""

import json
import subprocess
import requests
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QListWidget, QListWidgetItem, QSpinBox
from qfluentwidgets import (
    SubtitleLabel,
    BodyLabel,
    PrimaryPushButton,
    PushButton,
    ToggleButton,
    ComboBox,
    LineEdit,
    CardWidget,
    InfoBar,
    IndeterminateProgressRing,
    TransparentToolButton,
    FluentIcon,
    TextEdit,
    StrongBodyLabel,
)


class GTTPage(QWidget):
    """GTT automation page with window management, macros, and NLP integration"""

    def __init__(self, main_window):
        super().__init__()
        self.setObjectName("GTTPage")
        self.main_window = main_window
        self.cliproxy_url = "http://localhost:7599"
        self.gtt_daemon_pipe = "/tmp/gtt-universal.pipe"
        
        # Script builder state
        self.script_commands = []
        self.window_list = []
        
        # Get references to managers
        self.settings_manager = main_window.get_settings_manager()
        self.voice_processor = main_window.get_voice_processor()
        
        self.init_ui()
        self.connect_signals()
        self.refresh_windows()

    def init_ui(self):
        """Initialize the user interface"""
        # Main layout
        page_layout = QHBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)
        
        # Left panel: Window list and macros
        left_panel = self.create_left_panel()
        page_layout.addWidget(left_panel)
        
        # Center panel: Script builder
        center_panel = self.create_script_builder_panel()
        page_layout.addWidget(center_panel)
        
        # Right panel: NLP bar and execution
        right_panel = self.create_nlp_panel()
        page_layout.addWidget(right_panel)

    def create_left_panel(self):
        """Create left panel with window list and macros"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(20, 20, 10, 20)
        left_layout.setSpacing(15)
        
        # Window list section
        window_title = SubtitleLabel("Windows")
        window_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        left_layout.addWidget(window_title)
        
        # Window list with refresh button
        window_header = QHBoxLayout()
        self.refresh_windows_btn = TransparentToolButton(FluentIcon.SYNC, self)
        self.refresh_windows_btn.setToolTip("Refresh window list")
        self.refresh_windows_btn.clicked.connect(self.refresh_windows)
        window_header.addWidget(self.refresh_windows_btn)
        window_header.addStretch()
        left_layout.addLayout(window_header)
        
        self.window_list_widget = QListWidget()
        self.window_list_widget.setStyleSheet("""
            ListWidget {
                background-color: #1a1f26;
                border: 1px solid #30363d;
                border-radius: 8px;
                color: #e6edf3;
                font-size: 13px;
            }
            ListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            ListWidget::item:selected {
                background-color: #238636;
            }
            ListWidget::item:hover {
                background-color: #21262d;
            }
        """)
        self.window_list_widget.setMaximumHeight(200)
        left_layout.addWidget(self.window_list_widget)
        
        # Quick actions for selected window
        quick_actions_title = StrongBodyLabel("Quick Actions")
        left_layout.addWidget(quick_actions_title)
        
        self.focus_window_btn = PushButton("Focus Window")
        self.focus_window_btn.clicked.connect(self.focus_selected_window)
        left_layout.addWidget(self.focus_window_btn)
        
        self.close_window_btn = PushButton("Close Window")
        self.close_window_btn.clicked.connect(self.close_selected_window)
        left_layout.addWidget(self.close_window_btn)
        
        left_layout.addSpacing(20)
        
        # Macros section
        macros_title = SubtitleLabel("Macros")
        macros_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        left_layout.addWidget(macros_title)
        
        # Pre-loaded macros
        self.macro_buttons = []
        macros = [
            ("Focus Hyper", "focus_hyper"),
            ("Focus VS Code", "focus_vscode"),
            ("Focus Browser", "focus_browser"),
            ("Type Hello", "type_hello"),
            ("Copy/Paste", "copy_paste"),
            ("New Terminal", "new_terminal"),
            ("Screenshot", "screenshot"),
            ("Maximize Window", "maximize_window"),
        ]
        
        for macro_name, macro_id in macros:
            btn = PushButton(macro_name)
            btn.clicked.connect(lambda checked, mid=macro_id: self.execute_macro(mid))
            left_layout.addWidget(btn)
            self.macro_buttons.append(btn)
        
        left_layout.addStretch()
        
        return left_widget

    def create_script_builder_panel(self):
        """Create center panel for script building"""
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(10, 20, 10, 20)
        center_layout.setSpacing(15)
        
        # Script builder title
        script_title = SubtitleLabel("Script Builder")
        script_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        center_layout.addWidget(script_title)
        
        # Command type selector
        cmd_type_layout = QHBoxLayout()
        cmd_type_layout.addWidget(BodyLabel("Command:"))
        self.command_type_combo = ComboBox()
        self.command_type_combo.addItems([
            "Focus Window",
            "Launch App",
            "Type Text",
            "Send Keys",
            "Mouse Click",
            "Mouse Move",
            "Wait",
            "Screenshot",
        ])
        self.command_type_combo.currentIndexChanged.connect(self.on_command_type_changed)
        cmd_type_layout.addWidget(self.command_type_combo)
        cmd_type_layout.addStretch()
        center_layout.addLayout(cmd_type_layout)
        
        # Command parameters (dynamic based on type)
        self.command_params_widget = QWidget()
        self.command_params_layout = QVBoxLayout(self.command_params_widget)
        self.command_params_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addWidget(self.command_params_widget)
        
        # Add command button
        self.add_command_btn = PrimaryPushButton("Add Command to Script")
        self.add_command_btn.clicked.connect(self.add_command_to_script)
        center_layout.addWidget(self.add_command_btn)
        
        # Script command list
        script_list_title = StrongBodyLabel("Script Commands")
        center_layout.addWidget(script_list_title)
        
        self.script_list_widget = QListWidget()
        self.script_list_widget.setStyleSheet("""
            ListWidget {
                background-color: #1a1f26;
                border: 1px solid #30363d;
                border-radius: 8px;
                color: #e6edf3;
                font-size: 13px;
            }
            ListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            ListWidget::item:selected {
                background-color: #1f6feb;
            }
        """)
        self.script_list_widget.setMinimumHeight(200)
        center_layout.addWidget(self.script_list_widget)
        
        # Script controls
        script_controls = QHBoxLayout()
        self.remove_command_btn = PushButton("Remove Selected")
        self.remove_command_btn.clicked.connect(self.remove_selected_command)
        script_controls.addWidget(self.remove_command_btn)
        
        self.clear_script_btn = PushButton("Clear All")
        self.clear_script_btn.clicked.connect(self.clear_script)
        script_controls.addWidget(self.clear_script_btn)
        
        script_controls.addStretch()
        center_layout.addLayout(script_controls)
        
        # Execute script button
        self.execute_script_btn = PrimaryPushButton("▶ Execute Script")
        self.execute_script_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.execute_script_btn.clicked.connect(self.execute_script)
        center_layout.addWidget(self.execute_script_btn)
        
        # Progress indicator
        self.script_progress = IndeterminateProgressRing()
        self.script_progress.setVisible(False)
        center_layout.addWidget(self.script_progress, alignment=Qt.AlignmentFlag.AlignCenter)
        
        center_layout.addStretch()
        
        return center_widget

    def create_nlp_panel(self):
        """Create right panel for NLP input and voice control"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 20, 20, 20)
        right_layout.setSpacing(15)
        
        # NLP bar title
        nlp_title = SubtitleLabel("NLP Command Bar")
        nlp_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        right_layout.addWidget(nlp_title)
        
        # NLP input bar
        self.nlp_input = LineEdit()
        self.nlp_input.setPlaceholderText("Type natural language command...")
        self.nlp_input.setStyleSheet("""
            LineEdit {
                padding: 10px;
                font-size: 14px;
                border: 2px solid #30363d;
                border-radius: 8px;
                background-color: #1a1f26;
                color: #e6edf3;
            }
            LineEdit:focus {
                border-color: #1f6feb;
            }
        """)
        self.nlp_input.returnPressed.connect(self.send_nlp_command)
        right_layout.addWidget(self.nlp_input)
        
        # NLP send button
        self.send_nlp_btn = PrimaryPushButton("Send to CLIProxy")
        self.send_nlp_btn.clicked.connect(self.send_nlp_command)
        right_layout.addWidget(self.send_nlp_btn)
        
        right_layout.addSpacing(20)
        
        # Voice control section
        voice_title = SubtitleLabel("Voice Control")
        voice_title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        right_layout.addWidget(voice_title)
        
        # Voice input button
        self.voice_input_btn = PrimaryPushButton("🎤 Start Voice Command")
        self.voice_input_btn.setStyleSheet("font-size: 14px; padding: 12px;")
        self.voice_input_btn.clicked.connect(self.start_voice_command)
        right_layout.addWidget(self.voice_input_btn)
        
        # Voice status
        self.voice_status_label = BodyLabel("Ready")
        self.voice_status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        right_layout.addWidget(self.voice_status_label)
        
        right_layout.addSpacing(20)
        
        # Command history
        history_title = StrongBodyLabel("Command History")
        right_layout.addWidget(history_title)
        
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            ListWidget {
                background-color: #1a1f26;
                border: 1px solid #30363d;
                border-radius: 8px;
                color: #8b949e;
                font-size: 12px;
            }
        """)
        self.history_list.setMaximumHeight(150)
        right_layout.addWidget(self.history_list)
        
        # Execution log
        log_title = StrongBodyLabel("Execution Log")
        right_layout.addWidget(log_title)
        
        self.execution_log = TextEdit()
        self.execution_log.setReadOnly(True)
        self.execution_log.setMaximumHeight(200)
        self.execution_log.setStyleSheet("""
            TextEdit {
                background-color: #0d1117;
                color: #7d8590;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 8px;
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
                font-size: 11px;
            }
        """)
        right_layout.addWidget(self.execution_log)
        
        right_layout.addStretch()
        
        return right_widget

    def connect_signals(self):
        """Connect UI signals to handlers"""
        pass

    # === Window Management ===

    def refresh_windows(self):
        """Refresh window list using gtt --list"""
        try:
            result = subprocess.run(
                ["gtt", "--list", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                self.window_list = json.loads(result.stdout)
                self.window_list_widget.clear()
                
                for window in self.window_list:
                    app_id = window.get("app_id", "Unknown")
                    title = window.get("title", "Untitled")[:50]
                    wm_class = window.get("wm_class", "")
                    
                    display_text = f"{title}"
                    if wm_class:
                        display_text += f" ({wm_class})"
                    
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.UserRole, window.get("id"))
                    self.window_list_widget.addItem(item)
                
                InfoBar.success(
                    "Windows Refreshed",
                    f"Found {len(self.window_list)} windows",
                    parent=self,
                    duration=2000
                )
            else:
                InfoBar.error("Error", f"gtt --list failed: {result.stderr}", parent=self, duration=3000)
                
        except Exception as e:
            InfoBar.error("Error", f"Failed to get window list: {str(e)}", parent=self, duration=3000)

    def get_selected_window_id(self):
        """Get selected window ID from list"""
        current_item = self.window_list_widget.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None

    def focus_selected_window(self):
        """Focus the selected window"""
        window_id = self.get_selected_window_id()
        if window_id:
            self.execute_gtt_command(["gtt", "--focus", str(window_id)])
            self.log_execution(f"Focused window {window_id}")
        else:
            InfoBar.warning("No Selection", "Please select a window first", parent=self, duration=2000)

    def close_selected_window(self):
        """Close the selected window"""
        window_id = self.get_selected_window_id()
        if window_id:
            self.execute_gtt_command(["gtt", "--close", str(window_id)])
            self.log_execution(f"Closed window {window_id}")
            self.refresh_windows()
        else:
            InfoBar.warning("No Selection", "Please select a window first", parent=self, duration=2000)

    # === Macro Execution ===

    def execute_macro(self, macro_id):
        """Execute a pre-loaded macro"""
        macros = {
            "focus_hyper": ["gtt", "--launch", "Hyper"],
            "focus_vscode": ["gtt", "--focus", "Visual Studio Code"],
            "focus_browser": ["gtt", "--focus", "Firefox"],
            "type_hello": ["gtt", "--type", "Hello from GTT!"],
            "copy_paste": ["gtt", "--key", "ctrl+c", "--key", "ctrl+v"],
            "new_terminal": ["gtt", "--launch", "Hyper"],
            "screenshot": ["gtt", "--sc", "/tmp/screenshot.png"],
            "maximize_window": ["gtt", "--maximize", "active"],
        }
        
        if macro_id in macros:
            cmd = macros[macro_id]
            self.execute_gtt_command(cmd)
            self.log_execution(f"Executed macro: {macro_id}")

    # === Script Builder ===

    def on_command_type_changed(self, index):
        """Handle command type selection change"""
        # Clear existing params
        while self.command_params_layout.count():
            child = self.command_params_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add params based on command type
        cmd_type = self.command_type_combo.currentText()
        
        if cmd_type == "Focus Window":
            self.add_window_selector()
        elif cmd_type == "Launch App":
            self.add_app_name_input()
        elif cmd_type == "Type Text":
            self.add_text_input()
        elif cmd_type == "Send Keys":
            self.add_keys_input()
        elif cmd_type == "Mouse Click":
            self.add_mouse_click_selector()
        elif cmd_type == "Mouse Move":
            self.add_mouse_coords_input()
        elif cmd_type == "Wait":
            self.add_wait_duration_input()
        elif cmd_type == "Screenshot":
            self.add_screenshot_path_input()

    def add_window_selector(self):
        """Add window selector for Focus Window command"""
        self.command_params_layout.addWidget(BodyLabel("Select Window:"))
        self.param_window_combo = ComboBox()
        for window in self.window_list:
            title = window.get("title", "Untitled")[:50]
            self.param_window_combo.addItem(title, userData=window.get("id"))
        self.command_params_layout.addWidget(self.param_window_combo)

    def add_app_name_input(self):
        """Add app name input for Launch App command"""
        self.command_params_layout.addWidget(BodyLabel("App Name:"))
        self.param_app_name = LineEdit()
        self.param_app_name.setPlaceholderText("e.g., Firefox, Visual Studio Code")
        self.command_params_layout.addWidget(self.param_app_name)

    def add_text_input(self):
        """Add text input for Type Text command"""
        self.command_params_layout.addWidget(BodyLabel("Text to Type:"))
        self.param_text = LineEdit()
        self.param_text.setPlaceholderText("Enter text to type")
        self.command_params_layout.addWidget(self.param_text)

    def add_keys_input(self):
        """Add keys input for Send Keys command"""
        self.command_params_layout.addWidget(BodyLabel("Key Combination:"))
        self.param_keys = LineEdit()
        self.param_keys.setPlaceholderText("e.g., ctrl+c, super+Enter, alt+tab")
        self.command_params_layout.addWidget(self.param_keys)

    def add_mouse_click_selector(self):
        """Add mouse click selector"""
        self.command_params_layout.addWidget(BodyLabel("Mouse Button:"))
        self.param_mouse_button = ComboBox()
        self.param_mouse_button.addItems(["left", "right", "middle"])
        self.command_params_layout.addWidget(self.param_mouse_button)

    def add_mouse_coords_input(self):
        """Add mouse coordinates input"""
        coords_layout = QHBoxLayout()
        coords_layout.addWidget(BodyLabel("X:"))
        self.param_mouse_x = QSpinBox()
        self.param_mouse_x.setMaximum(9999)
        coords_layout.addWidget(self.param_mouse_x)
        coords_layout.addWidget(BodyLabel("Y:"))
        self.param_mouse_y = QSpinBox()
        self.param_mouse_y.setMaximum(9999)
        coords_layout.addWidget(self.param_mouse_y)
        self.command_params_layout.addLayout(coords_layout)

    def add_wait_duration_input(self):
        """Add wait duration input"""
        self.command_params_layout.addWidget(BodyLabel("Duration (ms):"))
        self.param_wait_duration = QSpinBox()
        self.param_wait_duration.setMaximum(60000)
        self.param_wait_duration.setValue(1000)
        self.command_params_layout.addWidget(self.param_wait_duration)

    def add_screenshot_path_input(self):
        """Add screenshot path input"""
        self.command_params_layout.addWidget(BodyLabel("Save Path:"))
        self.param_screenshot_path = LineEdit()
        self.param_screenshot_path.setText("/tmp/screenshot.png")
        self.command_params_layout.addWidget(self.param_screenshot_path)

    def add_command_to_script(self):
        """Add current command to script list"""
        cmd_type = self.command_type_combo.currentText()
        command_data = {"type": cmd_type, "params": {}}
        
        # Collect params based on command type
        if cmd_type == "Focus Window":
            if hasattr(self, 'param_window_combo'):
                command_data["params"]["window_id"] = self.param_window_combo.currentData()
        elif cmd_type == "Launch App":
            if hasattr(self, 'param_app_name'):
                command_data["params"]["app_name"] = self.param_app_name.text()
        elif cmd_type == "Type Text":
            if hasattr(self, 'param_text'):
                command_data["params"]["text"] = self.param_text.text()
        elif cmd_type == "Send Keys":
            if hasattr(self, 'param_keys'):
                command_data["params"]["keys"] = self.param_keys.text()
        elif cmd_type == "Mouse Click":
            if hasattr(self, 'param_mouse_button'):
                command_data["params"]["button"] = self.param_mouse_button.currentText()
        elif cmd_type == "Mouse Move":
            if hasattr(self, 'param_mouse_x') and hasattr(self, 'param_mouse_y'):
                command_data["params"]["x"] = self.param_mouse_x.value()
                command_data["params"]["y"] = self.param_mouse_y.value()
        elif cmd_type == "Wait":
            if hasattr(self, 'param_wait_duration'):
                command_data["params"]["duration"] = self.param_wait_duration.value()
        elif cmd_type == "Screenshot":
            if hasattr(self, 'param_screenshot_path'):
                command_data["params"]["path"] = self.param_screenshot_path.text()
        
        self.script_commands.append(command_data)
        
        # Add to list widget
        item_text = f"{cmd_type}"
        if command_data["params"]:
            params_str = ", ".join(f"{k}={v}" for k, v in command_data["params"].items())
            item_text += f" ({params_str})"
        
        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, len(self.script_commands) - 1)
        self.script_list_widget.addItem(item)
        
        InfoBar.success(
            "Command Added",
            f"Added {cmd_type} to script",
            parent=self,
            duration=1500
        )

    def remove_selected_command(self):
        """Remove selected command from script"""
        current_item = self.script_list_widget.currentItem()
        if current_item:
            index = current_item.data(Qt.UserRole)
            if 0 <= index < len(self.script_commands):
                self.script_commands.pop(index)
                self.script_list_widget.takeItem(self.script_list_widget.row(current_item))
                
                # Re-index remaining items
                for i in range(self.script_list_widget.count()):
                    item = self.script_list_widget.item(i)
                    item.setData(Qt.UserRole, i)

    def clear_script(self):
        """Clear all commands from script"""
        self.script_commands = []
        self.script_list_widget.clear()
        InfoBar.info("Script Cleared", "All commands removed", parent=self, duration=1500)

    def execute_script(self):
        """Execute the built script"""
        if not self.script_commands:
            InfoBar.warning("Empty Script", "Add commands to the script first", parent=self, duration=2000)
            return
        
        self.script_progress.setVisible(True)
        self.execute_script_btn.setEnabled(False)
        
        # Execute commands sequentially
        for i, cmd_data in enumerate(self.script_commands):
            self.execute_command_data(cmd_data)
            self.log_execution(f"[{i+1}/{len(self.script_commands)}] Executed {cmd_data['type']}")
        
        self.script_progress.setVisible(False)
        self.execute_script_btn.setEnabled(True)
        
        InfoBar.success(
            "Script Complete",
            f"Executed {len(self.script_commands)} commands",
            parent=self,
            duration=2000
        )

    def execute_command_data(self, cmd_data):
        """Execute a single command from script"""
        cmd_type = cmd_data["type"]
        params = cmd_data["params"]
        
        if cmd_type == "Focus Window":
            window_id = params.get("window_id")
            if window_id:
                self.execute_gtt_command(["gtt", "--focus", str(window_id)])
        elif cmd_type == "Launch App":
            app_name = params.get("app_name")
            if app_name:
                self.execute_gtt_command(["gtt", "--launch", app_name])
        elif cmd_type == "Type Text":
            text = params.get("text")
            if text:
                self.execute_gtt_command(["gtt", "--type", text])
        elif cmd_type == "Send Keys":
            keys = params.get("keys")
            if keys:
                self.execute_gtt_command(["gtt", "--key", keys])
        elif cmd_type == "Mouse Click":
            button = params.get("button")
            self.execute_gtt_command(["gtt", "--click", button or "left"])
        elif cmd_type == "Mouse Move":
            x = params.get("x", 0)
            y = params.get("y", 0)
            self.execute_gtt_command(["gtt", "--move", f"{x},{y}"])
        elif cmd_type == "Wait":
            duration = params.get("duration", 1000)
            QTimer.singleShot(duration, lambda: None)
        elif cmd_type == "Screenshot":
            path = params.get("path", "/tmp/screenshot.png")
            self.execute_gtt_command(["gtt", "--sc", path])

    # === NLP Integration ===

    def send_nlp_command(self):
        """Send NLP command to CLIProxy and parse response"""
        nlp_text = self.nlp_input.text().strip()
        if not nlp_text:
            InfoBar.warning("Empty Input", "Please enter a command", parent=self, duration=2000)
            return
        
        # Add to history
        self.history_list.addItem(f"📝 {nlp_text}")
        
        # Send to CLIProxy
        try:
            response = requests.post(
                f"{self.cliproxy_url}/v1/chat/completions",
                json={
                    "model": "qwen3-coder-plus",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a GTT (GreaterTouchTool) command generator. Convert natural language to GTT CLI commands. Output ONLY the gtt command, nothing else. Examples:\n- 'focus firefox' → 'gtt --focus firefox'\n- 'type hello world' → 'gtt --type hello world'\n- 'take screenshot' → 'gtt --sc /tmp/screenshot.png'\n- 'launch terminal' → 'gtt --launch Hyper'"
                        },
                        {
                            "role": "user",
                            "content": nlp_text
                        }
                    ]
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                gtt_command = data["choices"][0]["message"]["content"].strip()
                
                # Parse and execute the command
                self.log_execution(f"NLP → {gtt_command}")
                self.execute_parsed_command(gtt_command)
                
                InfoBar.success("NLP Success", f"Executed: {gtt_command}", parent=self, duration=2000)
            else:
                InfoBar.error("NLP Error", f"CLIProxy error: {response.status_code}", parent=self, duration=3000)
                
        except Exception as e:
            InfoBar.error("NLP Error", f"Failed: {str(e)}", parent=self, duration=3000)

    def execute_parsed_command(self, command):
        """Execute a parsed GTT command"""
        # Parse command string into parts
        if command.startswith("gtt "):
            command = command[4:]
        
        parts = command.split()
        if not parts:
            return
        
        # Build gtt command
        gtt_cmd = ["gtt"] + parts
        self.execute_gtt_command(gtt_cmd)

    def start_voice_command(self):
        """Start voice command using existing ASR pipeline"""
        self.voice_status_label.setText("Listening...")
        self.voice_status_label.setStyleSheet("color: #4A90E2; font-size: 12px;")
        self.voice_input_btn.setEnabled(False)
        
        # Use existing voice processor
        try:
            # Start recording
            success = self.voice_processor.start_recording()
            if success:
                # Show listening state
                InfoBar.info(
                    "Listening",
                    "Speak your GTT command now...",
                    parent=self,
                    duration=1000
                )
                
                # Stop after 5 seconds (for short commands)
                QTimer.singleShot(5000, self.process_voice_command)
            else:
                self.reset_voice_state()
                InfoBar.error("Error", "Failed to start voice recording", parent=self, duration=2000)
        except Exception as e:
            self.reset_voice_state()
            InfoBar.error("Error", f"Voice command failed: {str(e)}", parent=self, duration=3000)

    def process_voice_command(self):
        """Process recorded voice command"""
        try:
            # Stop recording
            audio_data = self.voice_processor.stop_recording()
            
            if audio_data is None or len(audio_data) == 0:
                self.reset_voice_state()
                InfoBar.warning("No Audio", "No voice detected", parent=self, duration=2000)
                return
            
            # Use existing ASR to transcribe
            transcription = self.voice_processor.transcribe_audio(audio_data)
            
            if transcription:
                self.voice_status_label.setText(f"Heard: '{transcription}'")
                self.nlp_input.setText(transcription)
                
                # Auto-send to NLP
                QTimer.singleShot(1000, self.send_nlp_command)
            else:
                self.reset_voice_state()
                InfoBar.warning("Transcription Failed", "Could not transcribe speech", parent=self, duration=2000)
                
        except Exception as e:
            self.reset_voice_state()
            InfoBar.error("Error", f"Voice processing failed: {str(e)}", parent=self, duration=3000)

    def reset_voice_state(self):
        """Reset voice command UI state"""
        self.voice_status_label.setText("Ready")
        self.voice_status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        self.voice_input_btn.setEnabled(True)

    # === Utility Methods ===

    def execute_gtt_command(self, cmd_list):
        """Execute a GTT command"""
        try:
            import os
            env = os.environ.copy()
            result = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                timeout=10,
                env=env
            )
            
            if result.returncode != 0:
                self.log_execution(f"Error: {result.stderr}")
            else:
                self.log_execution(f"Success: {result.stdout.strip()}")
                
        except Exception as e:
            self.log_execution(f"Exception: {str(e)}")

    def log_execution(self, message):
        """Log execution message"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.execution_log.append(f"[{timestamp}] {message}")
