"""
Context Awareness Service - Core service for GTT Context Awareness System

This service provides comprehensive context monitoring and rule evaluation for
automation scripts, hotkeys, and macros. It tracks system state, active applications,
window states, time periods, and user activity to determine when automation is allowed.

Features:
- Real-time context monitoring (active app, window, system state)
- Rule evaluation with AND/OR logic
- Priority-based rule ordering
- kernclip-bus integration for context publishing
- Context history tracking
- "Pin to Back" window control
- App-specific automation configuration

Usage:
    service = ContextAwarenessService()
    service.load_rules("/path/to/rules.json")
    service.start_monitoring()
    
    # Check if automation is allowed
    context = service.get_current_context()
    allowed, rule = service.is_automation_allowed("my_script", context)
"""

import os
import json
import time
import socket
import logging
import threading
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Tuple
from pathlib import Path
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Signal, QTimer, QThread

from src.models.context_rules import (
    ContextRule,
    ContextRuleCollection,
    AppContext,
    WindowContext,
    TimeContext,
    SystemContext,
    UserContext,
    ActionType,
    ContextType,
)


logger = logging.getLogger(__name__)


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
# Context Data Classes
# ============================================================================

@dataclass
class ContextSnapshot:
    """Snapshot of current system context"""
    timestamp: str
    app_id: str = ""
    wm_class: str = ""
    window_id: str = ""
    window_title: str = ""
    window_focused: bool = False
    window_pinned: bool = False
    window_state: str = ""
    window_width: int = 0
    window_height: int = 0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    network_status: str = ""
    internet_connected: bool = False
    battery_level: int = 100
    on_ac_power: bool = True
    idle_time_seconds: int = 0
    current_user: str = ""
    session_type: str = ""
    user_present: bool = True
    last_input_seconds_ago: int = 0
    running_processes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for rule evaluation"""
        return {
            "timestamp": self.timestamp,
            "app_id": self.app_id,
            "wm_class": self.wm_class,
            "window_id": self.window_id,
            "window_title": self.window_title,
            "window_focused": self.window_focused,
            "window_pinned": self.window_pinned,
            "window_state": self.window_state,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "network_status": self.network_status,
            "internet_connected": self.internet_connected,
            "battery_level": self.battery_level,
            "on_ac_power": self.on_ac_power,
            "idle_time_seconds": self.idle_time_seconds,
            "current_user": self.current_user,
            "session_type": self.session_type,
            "user_present": self.user_present,
            "last_input_seconds_ago": self.last_input_seconds_ago,
            "running_processes": self.running_processes,
        }


@dataclass
class ContextHistoryEntry:
    """Entry in context history"""
    timestamp: str
    previous_context: Dict[str, Any]
    new_context: Dict[str, Any]
    changed_fields: List[str]
    matching_rules: List[str]


# ============================================================================
# Context Monitor Thread
# ============================================================================

class ContextMonitorThread(QThread):
    """Background thread for continuous context monitoring"""
    context_changed = Signal(dict)  # Emits new context when changed
    error_occurred = Signal(str)    # Emits error message
    
    def __init__(self, service: "ContextAwarenessService", update_interval_ms: int = 500):
        super().__init__()
        self.service = service
        self.update_interval_ms = update_interval_ms
        self.running = False
        self.last_context: Dict[str, Any] = {}
        
    def run(self):
        """Main monitoring loop"""
        self.running = True
        last_change_time = 0
        
        while self.running:
            try:
                current_context = self.service._gather_context()
                current_time = time.time()
                
                # Check if context changed significantly
                if self._context_changed(current_context):
                    self.context_changed.emit(current_context)
                    self.last_context = current_context.copy()
                    last_change_time = current_time
                
                # Publish to bus periodically (every 5 seconds)
                if current_time - last_change_time > 5:
                    self.service._publish_context_to_bus(current_context)
                    last_change_time = current_time
                
                self.msleep(self.update_interval_ms)
                
            except Exception as e:
                self.error_occurred.emit(str(e))
                self.msleep(1000)  # Wait longer on error
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        self.wait(1000)
    
    def _context_changed(self, current: Dict[str, Any]) -> bool:
        """Check if context changed significantly"""
        if not self.last_context:
            return True
        
        # Check key fields for changes
        key_fields = ["app_id", "wm_class", "window_id", "window_title", 
                      "window_focused", "cpu_usage", "memory_usage",
                      "network_status", "battery_level"]
        
        for field in key_fields:
            if current.get(field) != self.last_context.get(field):
                return True
        
        return False


# ============================================================================
# Context Awareness Service
# ============================================================================

class ContextAwarenessService(QObject):
    """Main service for context awareness and rule evaluation
    
    This service provides:
    - Real-time context monitoring
    - Rule evaluation and matching
    - Context history tracking
    - kernclip-bus integration
    - "Pin to Back" window control
    - App-specific automation configuration
    """
    
    # Signals
    context_changed = Signal(dict)  # Emitted when context changes
    rule_matched = Signal(str, dict)  # Emitted when rule matches (rule_id, context)
    automation_blocked = Signal(str, str)  # Emitted when automation blocked (script_id, rule_name)
    error_occurred = Signal(str)  # Emitted on error
    
    def __init__(self, rules_file: Optional[str] = None):
        super().__init__()
        
        self.rules_collection = ContextRuleCollection()
        self.rules_file = rules_file or self._get_default_rules_path()
        
        self.bus_client = BusClient()
        self.monitor_thread: Optional[ContextMonitorThread] = None
        self.monitoring = False
        
        self.context_history: List[ContextHistoryEntry] = []
        self.max_history_size = 100
        
        self.pinned_windows: Dict[str, str] = {}  # window_id -> app_id
        
        self._rule_callbacks: Dict[str, List[Callable]] = {}
        self._context_cache: Dict[str, Any] = {}
        self._cache_timestamp: float = 0
        self._cache_ttl_seconds = 1.0  # Cache valid for 1 second
        
        # Load rules if file exists
        if self.rules_file and Path(self.rules_file).exists():
            self.load_rules(self.rules_file)
    
    def _get_default_rules_path(self) -> str:
        """Get default rules file path"""
        return str(Path(__file__).parent.parent / "data" / "app_context_rules.json")
    
    # ========================================================================
    # Rule Management
    # ========================================================================
    
    def load_rules(self, path: str) -> bool:
        """Load rules from JSON file"""
        try:
            self.rules_collection = ContextRuleCollection.load_from_file(path)
            logger.info(f"Loaded {len(self.rules_collection.rules)} rules from {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            return False
    
    def save_rules(self, path: Optional[str] = None) -> bool:
        """Save rules to JSON file"""
        path = path or self.rules_file
        try:
            self.rules_collection.save_to_file(path)
            logger.info(f"Saved {len(self.rules_collection.rules)} rules to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save rules: {e}")
            return False
    
    def add_rule(self, rule: ContextRule) -> str:
        """Add a rule to the collection"""
        rule_id = self.rules_collection.add_rule(rule)
        self._publish_rule_update("add", rule)
        return rule_id
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID"""
        rule = self.rules_collection.get_rule(rule_id)
        if rule:
            self.rules_collection.remove_rule(rule_id)
            self._publish_rule_update("remove", rule)
            return True
        return False
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update a rule's properties"""
        if self.rules_collection.update_rule(rule_id, updates):
            rule = self.rules_collection.get_rule(rule_id)
            self._publish_rule_update("update", rule)
            return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[ContextRule]:
        """Get a rule by ID"""
        return self.rules_collection.get_rule(rule_id)
    
    def get_all_rules(self) -> List[ContextRule]:
        """Get all rules"""
        return self.rules_collection.rules
    
    def get_rules_for_context(self, context_type: str) -> List[ContextRule]:
        """Get rules for a specific context type"""
        return [r for r in self.rules_collection.rules 
                if r.context_type.value == context_type]
    
    def _publish_rule_update(self, action: str, rule: ContextRule):
        """Publish rule update to bus"""
        if self.bus_client.available:
            data = json.dumps({
                "action": action,
                "rule": rule.to_dict()
            })
            self.bus_client.pub("conduit.context.rules", data)
    
    # ========================================================================
    # Context Gathering
    # ========================================================================
    
    def get_current_context(self, use_cache: bool = True) -> Dict[str, Any]:
        """Get current system context
        
        Args:
            use_cache: Use cached context if still valid
            
        Returns:
            Dictionary with current context data
        """
        current_time = time.time()
        
        # Use cache if valid
        if use_cache and self._context_cache:
            if current_time - self._cache_timestamp < self._cache_ttl_seconds:
                return self._context_cache.copy()
        
        # Gather fresh context
        context = self._gather_context()
        self._context_cache = context.copy()
        self._cache_timestamp = current_time
        
        return context
    
    def _gather_context(self) -> Dict[str, Any]:
        """Gather current system context from various sources"""
        snapshot = ContextSnapshot(
            timestamp=datetime.now().isoformat(),
            current_user=self._get_current_user(),
            session_type=self._get_session_type(),
        )
        
        # Get active window info
        window_info = self._get_active_window_info()
        snapshot.app_id = window_info.get("app_id", "")
        snapshot.wm_class = window_info.get("wm_class", "")
        snapshot.window_id = window_info.get("window_id", "")
        snapshot.window_title = window_info.get("window_title", "")
        snapshot.window_focused = window_info.get("focused", False)
        snapshot.window_pinned = window_info.get("pinned", False)
        snapshot.window_state = window_info.get("state", "")
        snapshot.window_width = window_info.get("width", 0)
        snapshot.window_height = window_info.get("height", 0)
        
        # Get system stats
        system_stats = self._get_system_stats()
        snapshot.cpu_usage = system_stats.get("cpu_usage", 0)
        snapshot.memory_usage = system_stats.get("memory_usage", 0)
        snapshot.battery_level = system_stats.get("battery_level", 100)
        snapshot.on_ac_power = system_stats.get("on_ac_power", True)
        
        # Get network status
        network_info = self._get_network_status()
        snapshot.network_status = network_info.get("status", "")
        snapshot.internet_connected = network_info.get("connected", False)
        
        # Get user activity
        user_activity = self._get_user_activity()
        snapshot.idle_time_seconds = user_activity.get("idle_time", 0)
        snapshot.last_input_seconds_ago = user_activity.get("last_input_ago", 0)
        snapshot.user_present = user_activity.get("present", True)
        
        # Get running processes
        snapshot.running_processes = self._get_running_processes()
        
        return snapshot.to_dict()
    
    def _get_active_window_info(self) -> Dict[str, Any]:
        """Get active window information using GTT"""
        try:
            result = subprocess.run(
                ["gtt", "--get-active"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                info = json.loads(result.stdout)
                return {
                    "app_id": info.get("app_id", ""),
                    "wm_class": info.get("wm_class", ""),
                    "window_id": info.get("id", ""),
                    "window_title": info.get("title", ""),
                    "focused": info.get("focused", True),
                    "pinned": info.get("pinned", False),
                    "state": info.get("state", ""),
                    "width": info.get("width", 0),
                    "height": info.get("height", 0),
                }
        except Exception as e:
            logger.debug(f"Failed to get active window: {e}")
        
        return {}
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        stats = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "battery_level": 100,
            "on_ac_power": True,
        }
        
        try:
            # CPU usage from /proc/stat
            with open("/proc/stat", "r") as f:
                line = f.readline()
                parts = line.split()
                if parts[0] == "cpu":
                    values = [int(x) for x in parts[1:8]]
                    total = sum(values)
                    idle = values[3]
                    stats["cpu_usage"] = round((1 - idle / total) * 100, 2) if total > 0 else 0
        except Exception:
            pass
        
        try:
            # Memory usage from /proc/meminfo
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
                mem_info = {}
                for line in lines[:10]:
                    parts = line.split()
                    if len(parts) >= 2:
                        mem_info[parts[0].rstrip(":")] = int(parts[1])
                
                total = mem_info.get("MemTotal", 1)
                available = mem_info.get("MemAvailable", total)
                stats["memory_usage"] = round((1 - available / total) * 100, 2)
        except Exception:
            pass
        
        try:
            # Battery status
            battery_path = Path("/sys/class/power_supply/BAT0")
            if battery_path.exists():
                capacity_file = battery_path / "capacity"
                if capacity_file.exists():
                    stats["battery_level"] = int(capacity_file.read_text().strip())
                
                status_file = battery_path / "status"
                if status_file.exists():
                    status = status_file.read_text().strip().lower()
                    stats["on_ac_power"] = status == "full" or status == "charging"
        except Exception:
            pass
        
        return stats
    
    def _get_network_status(self) -> Dict[str, Any]:
        """Get network status"""
        status = {
            "status": "disconnected",
            "connected": False,
        }
        
        try:
            # Check internet connectivity
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", "8.8.8.8"],
                capture_output=True,
                timeout=3
            )
            if result.returncode == 0:
                status["connected"] = True
                
                # Check connection type
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "TYPE,DEVICE", "connection", "show", "--active"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split("\n"):
                        if ":" in line:
                            conn_type, device = line.split(":", 1)
                            if conn_type.lower() == "wireless":
                                status["status"] = "wifi"
                                break
                            elif conn_type.lower() == "ethernet":
                                status["status"] = "ethernet"
                                break
                            elif conn_type.lower() == "gsm":
                                status["status"] = "mobile"
                                break
                    else:
                        status["status"] = "connected"
        except Exception:
            pass
        
        return status
    
    def _get_user_activity(self) -> Dict[str, Any]:
        """Get user activity information"""
        activity = {
            "idle_time": 0,
            "last_input_ago": 0,
            "present": True,
        }
        
        try:
            # Use xprintidle or similar to get idle time
            result = subprocess.run(
                ["xprintidle"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                idle_ms = int(result.stdout.strip())
                activity["idle_time"] = idle_ms // 1000
                activity["last_input_ago"] = idle_ms // 1000
                activity["present"] = activity["idle_time"] < 300  # 5 minutes threshold
        except Exception:
            # Fallback: assume user is present
            pass
        
        return activity
    
    def _get_current_user(self) -> str:
        """Get current username"""
        return os.environ.get("USER", os.environ.get("LOGNAME", "unknown"))
    
    def _get_session_type(self) -> str:
        """Get session type (wayland, x11, etc.)"""
        return os.environ.get("XDG_SESSION_TYPE", "unknown")
    
    def _get_running_processes(self) -> List[str]:
        """Get list of running process names"""
        processes = []
        try:
            for pid_dir in Path("/proc").glob("[0-9]*"):
                if pid_dir.is_dir():
                    try:
                        cmdline_file = pid_dir / "cmdline"
                        if cmdline_file.exists():
                            cmdline = cmdline_file.read_text().replace("\x00", " ").strip()
                            if cmdline:
                                proc_name = cmdline.split()[0].split("/")[-1]
                                processes.append(proc_name)
                    except Exception:
                        continue
        except Exception:
            pass
        
        return processes[:100]  # Limit to 100 processes
    
    # ========================================================================
    # Rule Evaluation
    # ========================================================================
    
    def evaluate_rules(self, script_id: str = "") -> List[ContextRule]:
        """Evaluate all rules against current context
        
        Args:
            script_id: Optional script ID for filtering
            
        Returns:
            List of matching rules in priority order
        """
        context = self.get_current_context()
        return self.rules_collection.evaluate(context)
    
    def is_automation_allowed(self, script_id: str, context: Optional[Dict] = None) -> Tuple[bool, Optional[ContextRule]]:
        """Check if automation is allowed for a script
        
        Args:
            script_id: Script identifier
            context: Optional context dict (uses current if not provided)
            
        Returns:
            Tuple of (is_allowed, blocking_rule)
        """
        if context is None:
            context = self.get_current_context()
        
        allowed, rule = self.rules_collection.is_allowed(script_id, context)
        
        if not allowed and rule:
            self.automation_blocked.emit(script_id, rule.name)
            logger.info(f"Automation blocked for '{script_id}': {rule.name}")
        
        return allowed, rule
    
    def check_context_before_execute(self, script_id: str) -> Tuple[bool, str, Optional[ContextRule]]:
        """Check context before executing a script
        
        Args:
            script_id: Script identifier
            
        Returns:
            Tuple of (can_execute, message, matching_rule)
        """
        allowed, rule = self.is_automation_allowed(script_id)
        
        if allowed:
            return True, "Context allows execution", rule
        else:
            return False, f"Blocked by rule: {rule.name if rule else 'unknown'}", rule
    
    def register_rule_callback(self, rule_id: str, callback: Callable[[Dict], None]):
        """Register a callback for when a specific rule matches"""
        if rule_id not in self._rule_callbacks:
            self._rule_callbacks[rule_id] = []
        self._rule_callbacks[rule_id].append(callback)
    
    def unregister_rule_callback(self, rule_id: str, callback: Callable):
        """Unregister a callback for a rule"""
        if rule_id in self._rule_callbacks:
            self._rule_callbacks[rule_id] = [c for c in self._rule_callbacks[rule_id] if c != callback]
    
    # ========================================================================
    # Monitoring
    # ========================================================================
    
    def start_monitoring(self, update_interval_ms: int = 500):
        """Start continuous context monitoring"""
        if self.monitoring:
            return
        
        self.monitor_thread = ContextMonitorThread(self, update_interval_ms)
        self.monitor_thread.context_changed.connect(self._on_context_changed)
        self.monitor_thread.error_occurred.connect(self.error_occurred.emit)
        self.monitor_thread.start()
        self.monitoring = True
        
        logger.info("Context monitoring started")
    
    def stop_monitoring(self):
        """Stop context monitoring"""
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread = None
            self.monitoring = False
            
            logger.info("Context monitoring stopped")
    
    def _on_context_changed(self, context: Dict[str, Any]):
        """Handle context change event"""
        # Publish to bus
        self._publish_context_to_bus(context)
        
        # Evaluate rules
        matching_rules = self.rules_collection.evaluate(context)
        
        # Emit signals
        self.context_changed.emit(context)
        
        for rule in matching_rules:
            self.rule_matched.emit(rule.id, context)
            
            # Call registered callbacks
            if rule.id in self._rule_callbacks:
                for callback in self._rule_callbacks[rule.id]:
                    try:
                        callback(context)
                    except Exception as e:
                        logger.error(f"Rule callback error: {e}")
        
        # Update history
        self._update_context_history(context, matching_rules)
    
    def _publish_context_to_bus(self, context: Dict[str, Any]):
        """Publish context to kernclip-bus"""
        if self.bus_client.available:
            data = json.dumps(context)
            self.bus_client.pub("conduit.context.changed", data)
    
    def _update_context_history(self, new_context: Dict[str, Any], matching_rules: List[ContextRule]):
        """Update context history"""
        if not self.context_history:
            entry = ContextHistoryEntry(
                timestamp=datetime.now().isoformat(),
                previous_context={},
                new_context=new_context,
                changed_fields=list(new_context.keys()),
                matching_rules=[r.id for r in matching_rules],
            )
            self.context_history.append(entry)
        else:
            last = self.context_history[-1]
            changed_fields = [k for k, v in new_context.items() 
                            if last.new_context.get(k) != v]
            
            if changed_fields:
                entry = ContextHistoryEntry(
                    timestamp=datetime.now().isoformat(),
                    previous_context=last.new_context,
                    new_context=new_context,
                    changed_fields=changed_fields,
                    matching_rules=[r.id for r in matching_rules],
                )
                self.context_history.append(entry)
        
        # Trim history
        while len(self.context_history) > self.max_history_size:
            self.context_history.pop(0)
    
    def get_context_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent context history"""
        return [
            {
                "timestamp": entry.timestamp,
                "changed_fields": entry.changed_fields,
                "matching_rules": entry.matching_rules,
            }
            for entry in self.context_history[-limit:]
        ]
    
    # ========================================================================
    # Pin to Back Window Control
    # ========================================================================
    
    def pin_window_to_back(self, window_id: str, app_id: str) -> bool:
        """Pin a window to the background
        
        The window remains automatable but stays behind other windows.
        
        Args:
            window_id: Window identifier
            app_id: Application identifier
            
        Returns:
            True if successful
        """
        try:
            # Use GTT to lower the window
            result = subprocess.run(
                ["gtt", "--minimize-window", window_id],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                self.pinned_windows[window_id] = app_id
                logger.info(f"Pinned window {window_id} ({app_id}) to back")
                return True
        except Exception as e:
            logger.error(f"Failed to pin window: {e}")
        
        return False
    
    def unpin_window(self, window_id: str) -> bool:
        """Unpin a window from background"""
        if window_id in self.pinned_windows:
            del self.pinned_windows[window_id]
            logger.info(f"Unpinned window {window_id}")
            return True
        return False
    
    def is_window_pinned(self, window_id: str) -> bool:
        """Check if window is pinned"""
        return window_id in self.pinned_windows
    
    def get_pinned_windows(self) -> Dict[str, str]:
        """Get all pinned windows"""
        return self.pinned_windows.copy()
    
    # ========================================================================
    # App-Specific Automation
    # ========================================================================
    
    def get_app_automation_config(self, app_id: str) -> Dict[str, Any]:
        """Get automation configuration for a specific app
        
        Returns:
            Dict with allowed_scripts, blocked_hotkeys, key_remappings, window_behavior
        """
        config = {
            "allowed_scripts": [],
            "blocked_hotkeys": [],
            "key_remappings": {},
            "window_behavior": {},
        }
        
        # Find rules for this app
        for rule in self.rules_collection.rules:
            for condition in rule.conditions:
                if condition.get("context_type") == ContextType.APP.value:
                    app_ctx = AppContext.from_dict(condition)
                    if app_ctx.app_id == app_id or app_ctx.wm_class == app_id:
                        if rule.action.action_type == ActionType.ALLOW:
                            script = rule.action.parameters.get("script_id")
                            if script:
                                config["allowed_scripts"].append(script)
                        elif rule.action.action_type == ActionType.BLOCK:
                            hotkey = rule.action.parameters.get("hotkey")
                            if hotkey:
                                config["blocked_hotkeys"].append(hotkey)
                        
                        # Window behavior
                        if rule.action.action_type == ActionType.PIN_BACK:
                            config["window_behavior"]["pin_to_back"] = True
        
        return config
    
    # ========================================================================
    # Import/Export
    # ========================================================================
    
    def export_rules(self, path: str, rule_ids: Optional[List[str]] = None) -> bool:
        """Export rules to JSON file
        
        Args:
            path: Output file path
            rule_ids: Optional list of rule IDs to export (exports all if None)
            
        Returns:
            True if successful
        """
        try:
            if rule_ids:
                rules = [r for r in self.rules_collection.rules if r.id in rule_ids]
                collection = ContextRuleCollection(rules=rules)
            else:
                collection = self.rules_collection
            
            collection.save_to_file(path)
            return True
        except Exception as e:
            logger.error(f"Failed to export rules: {e}")
            return False
    
    def import_rules(self, path: str, merge: bool = True) -> int:
        """Import rules from JSON file
        
        Args:
            path: Input file path
            merge: If True, merge with existing rules; if False, replace all
            
        Returns:
            Number of rules imported
        """
        try:
            imported = ContextRuleCollection.load_from_file(path)
            
            if merge:
                for rule in imported.rules:
                    self.rules_collection.add_rule(rule)
            else:
                self.rules_collection = imported
            
            self._publish_rule_update("import", None)
            return len(imported.rules)
        except Exception as e:
            logger.error(f"Failed to import rules: {e}")
            return 0
    
    # ========================================================================
    # Cleanup
    # ========================================================================
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_monitoring()
        self._rule_callbacks.clear()
        self.context_history.clear()
