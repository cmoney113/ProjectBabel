"""
GTT Page Script Execution Mixin.
Provides script execution and command handling methods for GTTPage.
"""

import subprocess
from typing import List, Dict
from qfluentwidgets import InfoBar


class ScriptExecutionMixin:
    """Mixin for script execution operations."""

    def on_execute_script(self, commands: List[dict], dry_run: bool) -> None:
        """Handle script execution from script builder."""
        if dry_run:
            self._preview_script(commands)
        else:
            self._execute_commands(commands)

    def _preview_script(self, commands: List[dict]) -> None:
        """Preview script without executing."""
        console = self.center_panel.console_panel
        console.append("=" * 60, "info")
        console.append("📋 DRY-RUN MODE - Script Preview", "info")
        console.append("=" * 60, "info")
        for i, cmd in enumerate(commands):
            params = cmd.get("params", {})
            params_str = ", ".join(f"{k}={v}" for k, v in params.items()) if params else ""
            display = f"[{i+1}] {cmd['type']}({params_str})" if params else f"[{i+1}] {cmd['type']}"
            console.append(display, "command")
        console.append("=" * 60, "info")
        InfoBar.info("Dry-run Complete", f"Previewed {len(commands)} commands", parent=self, duration=3000)

    def _execute_commands(self, commands: List[dict]) -> None:
        """Execute command list."""
        for i, cmd in enumerate(commands):
            self._execute_command_data(cmd)
            self.center_panel.console_panel.append(f"[{i+1}/{len(commands)}] {cmd['type']}", "info")
        InfoBar.success("Script Complete", f"Executed {len(commands)} commands", parent=self, duration=2000)

    def _execute_command_data(self, cmd_data: Dict) -> None:
        """Execute single command."""
        cmd_type = cmd_data["type"]
        params = cmd_data.get("params", {})
        handlers = {
            "Focus Window": lambda: self.execute_gtt_command(["gtt", "--focus", str(params.get("window_id"))]),
            "Close Window": lambda: self.execute_gtt_command(["gtt", "--close", str(params.get("window_id"))]),
            "Launch App": lambda: self.execute_gtt_command(["gtt", "--launch", params.get("app_name")]),
            "Type Text": lambda: self.execute_gtt_command(["gtt", "--type", params.get("text")]),
            "Send Keys": lambda: self.execute_gtt_command(["gtt", "--key", params.get("keys")]),
            "Screenshot": lambda: self.execute_gtt_command(["gtt", "--sc", params.get("path")]),
            "TermPipe Shell Command": lambda: self.execute_termpipe_command(params.get("command")),
        }
        if cmd_type in handlers and params.get(self._get_required_param(cmd_type)):
            handlers[cmd_type]()

    def _get_required_param(self, cmd_type: str) -> str:
        """Get required parameter name for command type."""
        param_map = {
            "Focus Window": "window_id", "Close Window": "window_id",
            "Launch App": "app_name", "Type Text": "text",
            "Send Keys": "keys", "Screenshot": "path",
            "TermPipe Shell Command": "command",
        }
        return param_map.get(cmd_type, "")

    def execute_termpipe_command(self, command: str) -> None:
        """Execute TermPipe command."""
        if not command:
            return
        try:
            self.center_panel.console_panel.append(f"⚡ TermPipe: {command}", "command")
            result = subprocess.run(["termf", "--exec", command], capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                self.center_panel.console_panel.append(result.stdout.strip(), "output")
            elif result.stderr:
                self.center_panel.console_panel.append(f"Error: {result.stderr}", "error")
        except Exception as e:
            self.center_panel.console_panel.append(f"Exception: {str(e)}", "error")

    def execute_gtt_command(self, cmd_list: List[str]) -> None:
        """Execute GTT command."""
        try:
            cmd_str = " ".join(cmd_list)
            self.center_panel.console_panel.append(f"▶ {cmd_str}", "command")
            result = subprocess.run(cmd_list, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.center_panel.console_panel.append(f"✗ {result.stderr}", "error")
            elif result.stdout:
                self.center_panel.console_panel.append(f"✓ {result.stdout.strip()}", "output")
        except Exception as e:
            self.center_panel.console_panel.append(f"✗ Exception: {str(e)}", "error")
