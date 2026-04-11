"""
Context Rule Editor Widget - Reusable dialog for creating/editing context rules

This widget provides a comprehensive UI for creating and editing context rules
with a visual condition builder, action selector, and test functionality.

Features:
- Visual condition builder with AND/OR logic groups
- Support for all context types (App, Window, Time, System, User)
- Action selector with parameters
- Test button to preview rule matches
- Fluent Design compliant (qfluentwidgets)

Usage:
    editor = ContextRuleEditor(parent)
    editor.rule_saved.connect(handle_rule_saved)
    editor.open()
    
    # Or edit existing rule:
    editor.load_rule(existing_rule)
    editor.open()
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QStackedWidget, QGroupBox, QGridLayout, QSplitter,
    QFileDialog, QMessageBox, QDialog, QDialogButtonBox,
)
from qfluentwidgets import (
    SubtitleLabel, BodyLabel, StrongBodyLabel, CaptionLabel,
    PrimaryPushButton, PushButton, ToggleButton, ComboBox,
    LineEdit, CardWidget, InfoBar, IndeterminateProgressRing,
    TransparentToolButton, FluentIcon, TextEdit, StrongBodyLabel,
    SwitchButton, ProgressBar, MessageBox, SearchLineEdit,
    FluentStyleSheet, isDarkTheme, SpinBox, TimeEdit,
    DateEdit, CheckBox, RadioButton, ToggleSwitch,
    InfoBarPosition, ComboBox, HyperlinkButton,
)

from src.models.context_rules import (
    ContextRule,
    AppContext,
    WindowContext,
    TimeContext,
    SystemContext,
    UserContext,
    RuleAction,
    ActionType,
    ContextType,
    MatchLogic,
    WindowState,
    NetworkStatus,
)


# ============================================================================
# Condition Builder Widget
# ============================================================================

class ConditionBuilderWidget(QWidget):
    """Widget for building conditions visually"""
    condition_added = Signal(dict)  # Emits condition dict
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Condition type selector
        type_layout = QHBoxLayout()
        type_layout.addWidget(BodyLabel("Condition Type:"))
        self.condition_type_combo = ComboBox()
        self.condition_type_combo.addItems([
            "Application Context",
            "Window Context",
            "Time Context",
            "System Context",
            "User Context",
        ])
        self.condition_type_combo.setMinimumHeight(35)
        self.condition_type_combo.currentIndexChanged.connect(self.on_type_changed)
        type_layout.addWidget(self.condition_type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # Condition parameters stack
        self.params_stack = QStackedWidget()
        
        # App context params
        self.app_params = self._create_app_params()
        self.params_stack.addWidget(self.app_params)
        
        # Window context params
        self.window_params = self._create_window_params()
        self.params_stack.addWidget(self.window_params)
        
        # Time context params
        self.time_params = self._create_time_params()
        self.params_stack.addWidget(self.time_params)
        
        # System context params
        self.system_params = self._create_system_params()
        self.params_stack.addWidget(self.system_params)
        
        # User context params
        self.user_params = self._create_user_params()
        self.params_stack.addWidget(self.user_params)
        
        layout.addWidget(self.params_stack)
        
        # Add button
        self.add_btn = PrimaryPushButton("Add Condition")
        self.add_btn.setMinimumHeight(40)
        self.add_btn.clicked.connect(self.add_condition)
        layout.addWidget(self.add_btn)
    
    def _create_app_params(self) -> QWidget:
        """Create app context parameters widget"""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # App ID
        layout.addWidget(BodyLabel("App ID:"), 0, 0)
        self.app_id_input = LineEdit()
        self.app_id_input.setPlaceholderText("e.g., code, firefox")
        self.app_id_input.setMinimumHeight(35)
        layout.addWidget(self.app_id_input, 0, 1)
        
        # WM Class
        layout.addWidget(BodyLabel("WM Class:"), 1, 0)
        self.wm_class_input = LineEdit()
        self.wm_class_input.setPlaceholderText("e.g., Code, Firefox")
        self.wm_class_input.setMinimumHeight(35)
        layout.addWidget(self.wm_class_input, 1, 1)
        
        # Title contains
        layout.addWidget(BodyLabel("Title Contains:"), 2, 0)
        self.title_contains_input = LineEdit()
        self.title_contains_input.setPlaceholderText("Window title substring")
        self.title_contains_input.setMinimumHeight(35)
        layout.addWidget(self.title_contains_input, 2, 1)
        
        # Title pattern (regex)
        layout.addWidget(BodyLabel("Title Pattern (regex):"), 3, 0)
        self.title_pattern_input = LineEdit()
        self.title_pattern_input.setPlaceholderText("Regex pattern for title")
        self.title_pattern_input.setMinimumHeight(35)
        layout.addWidget(self.title_pattern_input, 3, 1)
        
        # Match mode
        layout.addWidget(BodyLabel("Match Mode:"), 4, 0)
        self.app_match_mode_combo = ComboBox()
        self.app_match_mode_combo.addItems(["exact", "contains", "regex", "starts_with"])
        self.app_match_mode_combo.setMinimumHeight(35)
        layout.addWidget(self.app_match_mode_combo, 4, 1)
        
        layout.setColumnStretch(2, 1)
        return widget
    
    def _create_window_params(self) -> QWidget:
        """Create window context parameters widget"""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Focus state
        layout.addWidget(BodyLabel("Focus State:"), 0, 0)
        self.window_focus_combo = ComboBox()
        self.window_focus_combo.addItems(["Any", "Focused", "Background"])
        self.window_focus_combo.setMinimumHeight(35)
        layout.addWidget(self.window_focus_combo, 0, 1)
        
        # Pinned state
        layout.addWidget(BodyLabel("Pinned:"), 1, 0)
        self.window_pinned_combo = ComboBox()
        self.window_pinned_combo.addItems(["Any", "Pinned", "Not Pinned"])
        self.window_pinned_combo.setMinimumHeight(35)
        layout.addWidget(self.window_pinned_combo, 1, 1)
        
        # Window state
        layout.addWidget(BodyLabel("Window State:"), 2, 0)
        self.window_state_combo = ComboBox()
        self.window_state_combo.addItems(["Any", "Maximized", "Minimized", "Fullscreen"])
        self.window_state_combo.setMinimumHeight(35)
        layout.addWidget(self.window_state_combo, 2, 1)
        
        # Min width
        layout.addWidget(BodyLabel("Min Width:"), 3, 0)
        self.min_width_spin = SpinBox()
        self.min_width_spin.setRange(0, 99999)
        self.min_width_spin.setMinimumHeight(35)
        layout.addWidget(self.min_width_spin, 3, 1)
        
        # Min height
        layout.addWidget(BodyLabel("Min Height:"), 4, 0)
        self.min_height_spin = SpinBox()
        self.min_height_spin.setRange(0, 99999)
        self.min_height_spin.setMinimumHeight(35)
        layout.addWidget(self.min_height_spin, 4, 1)
        
        layout.setColumnStretch(2, 1)
        return widget
    
    def _create_time_params(self) -> QWidget:
        """Create time context parameters widget"""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Time range start
        layout.addWidget(BodyLabel("Time Range Start:"), 0, 0)
        self.time_start_edit = TimeEdit()
        self.time_start_edit.setMinimumHeight(35)
        layout.addWidget(self.time_start_edit, 0, 1)
        
        # Time range end
        layout.addWidget(BodyLabel("Time Range End:"), 1, 0)
        self.time_end_edit = TimeEdit()
        self.time_end_edit.setMinimumHeight(35)
        layout.addWidget(self.time_end_edit, 1, 1)
        
        # Days of week
        layout.addWidget(BodyLabel("Days of Week:"), 2, 0)
        days_widget = QWidget()
        days_layout = QHBoxLayout(days_widget)
        days_layout.setContentsMargins(0, 0, 0, 0)
        self.day_checkboxes = {}
        for i, day in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            cb = CheckBox(day)
            self.day_checkboxes[i] = cb
            days_layout.addWidget(cb)
        layout.addWidget(days_widget, 2, 1)
        
        # Recurring
        layout.addWidget(BodyLabel("Recurring:"), 3, 0)
        recurring_widget = QWidget()
        recurring_layout = QHBoxLayout(recurring_widget)
        recurring_layout.setContentsMargins(0, 0, 0, 0)
        self.recurring_daily_cb = CheckBox("Daily")
        self.recurring_weekly_cb = CheckBox("Weekly")
        recurring_layout.addWidget(self.recurring_daily_cb)
        recurring_layout.addWidget(self.recurring_weekly_cb)
        layout.addWidget(recurring_widget, 3, 1)
        
        layout.setColumnStretch(2, 1)
        return widget
    
    def _create_system_params(self) -> QWidget:
        """Create system context parameters widget"""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Max CPU
        layout.addWidget(BodyLabel("Max CPU %:"), 0, 0)
        self.max_cpu_spin = SpinBox()
        self.max_cpu_spin.setRange(0, 100)
        self.max_cpu_spin.setMinimumHeight(35)
        layout.addWidget(self.max_cpu_spin, 0, 1)
        
        # Max Memory
        layout.addWidget(BodyLabel("Max Memory %:"), 1, 0)
        self.max_memory_spin = SpinBox()
        self.max_memory_spin.setRange(0, 100)
        self.max_memory_spin.setMinimumHeight(35)
        layout.addWidget(self.max_memory_spin, 1, 1)
        
        # Network status
        layout.addWidget(BodyLabel("Network:"), 2, 0)
        self.network_combo = ComboBox()
        self.network_combo.addItems(["Any", "Connected", "Disconnected", "WiFi", "Ethernet"])
        self.network_combo.setMinimumHeight(35)
        layout.addWidget(self.network_combo, 2, 1)
        
        # Min Battery
        layout.addWidget(BodyLabel("Min Battery %:"), 3, 0)
        self.min_battery_spin = SpinBox()
        self.min_battery_spin.setRange(0, 100)
        self.min_battery_spin.setMinimumHeight(35)
        layout.addWidget(self.min_battery_spin, 3, 1)
        
        # On AC power
        layout.addWidget(BodyLabel("Power:"), 4, 0)
        self.power_combo = ComboBox()
        self.power_combo.addItems(["Any", "On AC", "On Battery"])
        self.power_combo.setMinimumHeight(35)
        layout.addWidget(self.power_combo, 4, 1)
        
        # Require process
        layout.addWidget(BodyLabel("Require Process:"), 5, 0)
        self.require_process_input = LineEdit()
        self.require_process_input.setPlaceholderText("Process name that must be running")
        self.require_process_input.setMinimumHeight(35)
        layout.addWidget(self.require_process_input, 5, 1)
        
        layout.setColumnStretch(2, 1)
        return widget
    
    def _create_user_params(self) -> QWidget:
        """Create user context parameters widget"""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Max idle time
        layout.addWidget(BodyLabel("Max Idle Time (sec):"), 0, 0)
        self.max_idle_spin = SpinBox()
        self.max_idle_spin.setRange(0, 86400)
        self.max_idle_spin.setMinimumHeight(35)
        layout.addWidget(self.max_idle_spin, 0, 1)
        
        # Require user
        layout.addWidget(BodyLabel("Require User:"), 1, 0)
        self.require_user_input = LineEdit()
        self.require_user_input.setPlaceholderText("Username")
        self.require_user_input.setMinimumHeight(35)
        layout.addWidget(self.require_user_input, 1, 1)
        
        # Session type
        layout.addWidget(BodyLabel("Session Type:"), 2, 0)
        self.session_combo = ComboBox()
        self.session_combo.addItems(["Any", "wayland", "x11"])
        self.session_combo.setMinimumHeight(35)
        layout.addWidget(self.session_combo, 2, 1)
        
        layout.setColumnStretch(2, 1)
        return widget
    
    def on_type_changed(self, index: int):
        """Handle condition type change"""
        self.params_stack.setCurrentIndex(index)
    
    def add_condition(self):
        """Build condition from inputs and emit signal"""
        condition_type = self.condition_type_combo.currentText()
        condition = {"context_type": ""}
        
        if condition_type == "Application Context":
            condition = self._build_app_condition()
        elif condition_type == "Window Context":
            condition = self._build_window_condition()
        elif condition_type == "Time Context":
            condition = self._build_time_condition()
        elif condition_type == "System Context":
            condition = self._build_system_condition()
        elif condition_type == "User Context":
            condition = self._build_user_condition()
        
        if condition:
            self.condition_added.emit(condition)
            InfoBar.success(
                "Condition Added",
                f"Added {condition_type} condition",
                parent=self.parent().parent() if self.parent() else None,
                duration=2000
            )
    
    def _build_app_condition(self) -> Dict[str, Any]:
        """Build app context condition"""
        condition = {
            "context_type": ContextType.APP.value,
        }
        
        if self.app_id_input.text().strip():
            condition["app_id"] = self.app_id_input.text().strip()
        if self.wm_class_input.text().strip():
            condition["wm_class"] = self.wm_class_input.text().strip()
        if self.title_contains_input.text().strip():
            condition["title_contains"] = self.title_contains_input.text().strip()
        if self.title_pattern_input.text().strip():
            condition["title_pattern"] = self.title_pattern_input.text().strip()
        
        condition["match_mode"] = self.app_match_mode_combo.currentText()
        
        # Only return if at least one field is set
        if len(condition) > 1:
            return condition
        return {}
    
    def _build_window_condition(self) -> Dict[str, Any]:
        """Build window context condition"""
        condition = {
            "context_type": ContextType.WINDOW.value,
        }
        
        focus = self.window_focus_combo.currentText()
        if focus == "Focused":
            condition["is_focused"] = True
        elif focus == "Background":
            condition["is_background"] = True
        
        pinned = self.window_pinned_combo.currentText()
        if pinned == "Pinned":
            condition["is_pinned"] = True
        elif pinned == "Not Pinned":
            condition["is_pinned"] = False
        
        state = self.window_state_combo.currentText()
        if state != "Any":
            condition["window_states"] = [state.lower()]
        
        if self.min_width_spin.value() > 0:
            condition["min_width"] = self.min_width_spin.value()
        if self.min_height_spin.value() > 0:
            condition["min_height"] = self.min_height_spin.value()
        
        if len(condition) > 1:
            return condition
        return {}
    
    def _build_time_condition(self) -> Dict[str, Any]:
        """Build time context condition"""
        condition = {
            "context_type": ContextType.TIME.value,
        }
        
        # Time range
        start = self.time_start_edit.time()
        end = self.time_end_edit.time()
        if start.isValid() and end.isValid():
            condition["time_ranges"] = [[start.toString("HH:mm"), end.toString("HH:mm")]]
        
        # Days of week
        days = [i for i, cb in self.day_checkboxes.items() if cb.isChecked()]
        if days:
            condition["days_of_week"] = days
        
        # Recurring
        if self.recurring_daily_cb.isChecked():
            condition["recurring_daily"] = True
        if self.recurring_weekly_cb.isChecked():
            condition["recurring_weekly"] = True
        
        if len(condition) > 1:
            return condition
        return {}
    
    def _build_system_condition(self) -> Dict[str, Any]:
        """Build system context condition"""
        condition = {
            "context_type": ContextType.SYSTEM.value,
        }
        
        if self.max_cpu_spin.value() > 0:
            condition["max_cpu_usage"] = self.max_cpu_spin.value()
        if self.max_memory_spin.value() > 0:
            condition["max_memory_usage"] = self.max_memory_spin.value()
        
        network = self.network_combo.currentText()
        if network != "Any":
            condition["network_status"] = network.lower()
        
        if self.min_battery_spin.value() > 0:
            condition["min_battery_level"] = self.min_battery_spin.value()
        
        power = self.power_combo.currentText()
        if power == "On AC":
            condition["on_ac_power"] = True
        elif power == "On Battery":
            condition["on_ac_power"] = False
        
        if self.require_process_input.text().strip():
            condition["require_process"] = self.require_process_input.text().strip()
        
        if len(condition) > 1:
            return condition
        return {}
    
    def _build_user_condition(self) -> Dict[str, Any]:
        """Build user context condition"""
        condition = {
            "context_type": ContextType.USER.value,
        }
        
        if self.max_idle_spin.value() > 0:
            condition["max_idle_time"] = self.max_idle_spin.value()
        
        if self.require_user_input.text().strip():
            condition["require_user"] = self.require_user_input.text().strip()
        
        session = self.session_combo.currentText()
        if session != "Any":
            condition["session_types"] = [session.lower()]
        
        if len(condition) > 1:
            return condition
        return {}


# ============================================================================
# Action Selector Widget
# ============================================================================

class ActionSelectorWidget(QWidget):
    """Widget for selecting and configuring rule actions"""
    action_changed = Signal(dict)  # Emits action dict
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Action type selector
        type_layout = QHBoxLayout()
        type_layout.addWidget(BodyLabel("Action Type:"))
        self.action_type_combo = ComboBox()
        self.action_type_combo.addItems([
            "Allow Automation",
            "Block Automation",
            "Modify Automation",
            "Trigger Different Automation",
            "Pin Window to Back",
            "Show Notification",
        ])
        self.action_type_combo.setMinimumHeight(35)
        self.action_type_combo.currentIndexChanged.connect(self.on_action_type_changed)
        type_layout.addWidget(self.action_type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # Action parameters stack
        self.params_stack = QStackedWidget()
        
        # Allow action params (none)
        allow_widget = QWidget()
        allow_layout = QVBoxLayout(allow_widget)
        allow_layout.addWidget(BodyLabel("Automation will be allowed when this rule matches."))
        self.params_stack.addWidget(allow_widget)
        
        # Block action params (none)
        block_widget = QWidget()
        block_layout = QVBoxLayout(block_widget)
        block_layout.addWidget(BodyLabel("Automation will be blocked when this rule matches."))
        self.params_stack.addWidget(block_widget)
        
        # Modify action params
        self.modify_params = self._create_modify_params()
        self.params_stack.addWidget(self.modify_params)
        
        # Trigger action params
        self.trigger_params = self._create_trigger_params()
        self.params_stack.addWidget(self.trigger_params)
        
        # Pin back action params (none)
        pin_widget = QWidget()
        pin_layout = QVBoxLayout(pin_widget)
        pin_layout.addWidget(BodyLabel("Window will be pinned to background."))
        self.params_stack.addWidget(pin_widget)
        
        # Notify action params
        self.notify_params = self._create_notify_params()
        self.params_stack.addWidget(self.notify_params)
        
        layout.addWidget(self.params_stack)
    
    def _create_modify_params(self) -> QWidget:
        """Create modify action parameters"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        layout.addWidget(BodyLabel("New Parameters (JSON):"))
        self.modify_params_input = TextEdit()
        self.modify_params_input.setPlaceholderText('{"param1": "value1", "param2": 123}')
        self.modify_params_input.setMinimumHeight(100)
        layout.addWidget(self.modify_params_input)
        
        return widget
    
    def _create_trigger_params(self) -> QWidget:
        """Create trigger action parameters"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        layout.addWidget(BodyLabel("Script/Command to Trigger:"))
        self.trigger_script_input = LineEdit()
        self.trigger_script_input.setPlaceholderText("Script ID or command")
        self.trigger_script_input.setMinimumHeight(35)
        layout.addWidget(self.trigger_script_input)
        
        return widget
    
    def _create_notify_params(self) -> QWidget:
        """Create notify action parameters"""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        layout.addWidget(BodyLabel("Notification Title:"), 0, 0)
        self.notify_title_input = LineEdit()
        self.notify_title_input.setPlaceholderText("Notification title")
        self.notify_title_input.setMinimumHeight(35)
        layout.addWidget(self.notify_title_input, 0, 1)
        
        layout.addWidget(BodyLabel("Notification Message:"), 1, 0)
        self.notify_message_input = LineEdit()
        self.notify_message_input.setPlaceholderText("Notification message")
        self.notify_message_input.setMinimumHeight(35)
        layout.addWidget(self.notify_message_input, 1, 1)
        
        layout.setColumnStretch(2, 1)
        return widget
    
    def on_action_type_changed(self, index: int):
        """Handle action type change"""
        self.params_stack.setCurrentIndex(index)
        self._emit_action()
    
    def get_action(self) -> Dict[str, Any]:
        """Get current action configuration"""
        action_type = self.action_type_combo.currentText()
        action_map = {
            "Allow Automation": ActionType.ALLOW.value,
            "Block Automation": ActionType.BLOCK.value,
            "Modify Automation": ActionType.MODIFY.value,
            "Trigger Different Automation": ActionType.TRIGGER.value,
            "Pin Window to Back": ActionType.PIN_BACK.value,
            "Show Notification": ActionType.NOTIFY.value,
        }
        
        action = {
            "action_type": action_map.get(action_type, ActionType.ALLOW.value),
            "parameters": {},
        }
        
        if action_type == "Modify Automation":
            try:
                params = json.loads(self.modify_params_input.toPlainText())
                action["modify_params"] = params
            except json.JSONDecodeError:
                pass
        
        elif action_type == "Trigger Different Automation":
            action["trigger_script"] = self.trigger_script_input.text().strip()
        
        elif action_type == "Show Notification":
            action["notification_title"] = self.notify_title_input.text().strip()
            action["notification_message"] = self.notify_message_input.text().strip()
        
        return action
    
    def _emit_action(self):
        """Emit current action"""
        self.action_changed.emit(self.get_action())


# ============================================================================
# Context Rule Editor Dialog
# ============================================================================

class ContextRuleEditor(QDialog):
    """Dialog for creating and editing context rules"""
    
    rule_saved = Signal(ContextRule)  # Emitted when rule is saved
    rule_tested = Signal(dict)  # Emitted when rule is tested
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Context Rule Editor")
        self.setModal(True)
        self.setMinimumSize(800, 700)
        self.resize(900, 800)
        
        self.current_rule: Optional[ContextRule] = None
        self.conditions: List[Dict[str, Any]] = []
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = SubtitleLabel("Context Rule Editor")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title)
        
        # Basic info section
        basic_group = QGroupBox("Basic Information")
        basic_layout = QGridLayout(basic_group)
        basic_layout.setSpacing(10)
        
        # Name
        basic_layout.addWidget(BodyLabel("Rule Name:"), 0, 0)
        self.name_input = LineEdit()
        self.name_input.setPlaceholderText("Enter rule name")
        self.name_input.setMinimumHeight(35)
        basic_layout.addWidget(self.name_input, 0, 1)
        
        # Description
        basic_layout.addWidget(BodyLabel("Description:"), 1, 0)
        self.description_input = LineEdit()
        self.description_input.setPlaceholderText("Enter rule description")
        self.description_input.setMinimumHeight(35)
        basic_layout.addWidget(self.description_input, 1, 1)
        
        # Enabled
        basic_layout.addWidget(BodyLabel("Enabled:"), 2, 0)
        self.enabled_switch = SwitchButton()
        self.enabled_switch.setChecked(True)
        basic_layout.addWidget(self.enabled_switch, 2, 1)
        
        # Priority
        basic_layout.addWidget(BodyLabel("Priority:"), 3, 0)
        self.priority_spin = SpinBox()
        self.priority_spin.setRange(-1000, 1000)
        self.priority_spin.setMinimumHeight(35)
        basic_layout.addWidget(self.priority_spin, 3, 1)
        
        # Match logic
        basic_layout.addWidget(BodyLabel("Match Logic:"), 4, 0)
        self.match_logic_combo = ComboBox()
        self.match_logic_combo.addItems(["AND (All conditions must match)", "OR (Any condition matches)"])
        self.match_logic_combo.setMinimumHeight(35)
        basic_layout.addWidget(self.match_logic_combo, 4, 1)
        
        layout.addWidget(basic_group)
        
        # Conditions section
        conditions_group = QGroupBox("Conditions")
        conditions_layout = QVBoxLayout(conditions_group)
        
        # Conditions list
        self.conditions_list_widget = QListWidget()
        self.conditions_list_widget.setStyleSheet("""
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
        self.conditions_list_widget.setMinimumHeight(150)
        conditions_layout.addWidget(self.conditions_list_widget)
        
        # Condition builder
        self.condition_builder = ConditionBuilderWidget()
        self.condition_builder.condition_added.connect(self.on_condition_added)
        conditions_layout.addWidget(self.condition_builder)
        
        layout.addWidget(conditions_group)
        
        # Action section
        action_group = QGroupBox("Action")
        action_layout = QVBoxLayout(action_group)
        
        self.action_selector = ActionSelectorWidget()
        action_layout.addWidget(self.action_selector)
        
        layout.addWidget(action_group)
        
        # Test section
        test_layout = QHBoxLayout()
        test_layout.addWidget(BodyLabel("Test this rule against current context to see if it would match."))
        test_layout.addStretch()
        self.test_btn = PushButton("🧪 Test Rule")
        self.test_btn.setMinimumHeight(35)
        self.test_btn.clicked.connect(self.test_rule)
        test_layout.addWidget(self.test_btn)
        layout.addLayout(test_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Save).setText("Save Rule")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
        button_box.accepted.connect(self.save_rule)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_rule(self, rule: ContextRule):
        """Load existing rule into editor"""
        self.current_rule = rule
        
        self.name_input.setText(rule.name)
        self.description_input.setText(rule.description)
        self.enabled_switch.setChecked(rule.enabled)
        self.priority_spin.setValue(rule.priority)
        
        # Match logic
        if rule.match_logic == MatchLogic.OR:
            self.match_logic_combo.setCurrentIndex(1)
        else:
            self.match_logic_combo.setCurrentIndex(0)
        
        # Conditions
        self.conditions = rule.conditions.copy()
        self._update_conditions_list()
        
        # Action
        action_type_map = {
            ActionType.ALLOW.value: 0,
            ActionType.BLOCK.value: 1,
            ActionType.MODIFY.value: 2,
            ActionType.TRIGGER.value: 3,
            ActionType.PIN_BACK.value: 4,
            ActionType.NOTIFY.value: 5,
        }
        action_index = action_type_map.get(rule.action.action_type.value, 0)
        self.action_selector.action_type_combo.setCurrentIndex(action_index)
    
    def on_condition_added(self, condition: Dict[str, Any]):
        """Handle condition added from builder"""
        self.conditions.append(condition)
        self._update_conditions_list()
    
    def _update_conditions_list(self):
        """Update conditions list widget"""
        self.conditions_list_widget.clear()
        
        for i, condition in enumerate(self.conditions):
            ctx_type = condition.get("context_type", "unknown")
            
            # Create display text
            if ctx_type == ContextType.APP.value:
                text = f"📱 App: {condition.get('app_id', condition.get('wm_class', 'Any'))}"
            elif ctx_type == ContextType.WINDOW.value:
                text = f"🪟 Window: {condition.get('is_focused', 'Any')}"
            elif ctx_type == ContextType.TIME.value:
                text = f"🕐 Time: {condition.get('time_ranges', ['Any'])[0] if condition.get('time_ranges') else 'Any'}"
            elif ctx_type == ContextType.SYSTEM.value:
                text = f"💻 System: CPU≤{condition.get('max_cpu_usage', 'Any')}%"
            elif ctx_type == ContextType.USER.value:
                text = f"👤 User: Idle≤{condition.get('max_idle_time', 'Any')}s"
            else:
                text = f"❓ {ctx_type}"
            
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, i)
            self.conditions_list_widget.addItem(item)
    
    def test_rule(self):
        """Test rule against current context"""
        # Import service to get current context
        try:
            from src.services.context_awareness_service import ContextAwarenessService
            service = ContextAwarenessService()
            context = service.get_current_context()
            
            # Build temporary rule
            rule = self._build_rule()
            matches = rule.matches(context)
            
            if matches:
                InfoBar.success(
                    "Rule Matches",
                    "This rule would match the current context!",
                    parent=self,
                    duration=3000
                )
            else:
                InfoBar.warning(
                    "Rule Does Not Match",
                    "This rule would NOT match the current context.",
                    parent=self,
                    duration=3000
                )
            
            self.rule_tested.emit({"matches": matches, "context": context})
            
        except Exception as e:
            InfoBar.error("Test Failed", str(e), parent=self, duration=4000)
    
    def _build_rule(self) -> ContextRule:
        """Build rule from current inputs"""
        match_logic = MatchLogic.AND
        if self.match_logic_combo.currentIndex() == 1:
            match_logic = MatchLogic.OR
        
        action_data = self.action_selector.get_action()
        action = RuleAction(
            action_type=ActionType(action_data["action_type"]),
            parameters=action_data.get("parameters", {}),
            modify_params=action_data.get("modify_params", {}),
            trigger_script=action_data.get("trigger_script"),
            notification_title=action_data.get("notification_title"),
            notification_message=action_data.get("notification_message"),
        )
        
        rule = ContextRule(
            name=self.name_input.text().strip() or "Unnamed Rule",
            description=self.description_input.text().strip(),
            enabled=self.enabled_switch.isChecked(),
            priority=self.priority_spin.value(),
            match_logic=match_logic,
            conditions=self.conditions.copy(),
            action=action,
        )
        
        if self.current_rule:
            rule.id = self.current_rule.id
            rule.created_at = self.current_rule.created_at
        
        return rule
    
    def save_rule(self):
        """Save rule and emit signal"""
        rule = self._build_rule()
        self.rule_saved.emit(rule)
        self.accept()
