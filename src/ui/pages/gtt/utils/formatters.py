"""
Formatting utilities for GTT page components.
Provides consistent formatting for console output, timestamps, and command display.
"""

from datetime import datetime
from typing import Dict, Any


def format_timestamp() -> str:
    """Return current time formatted as HH:MM:SS"""
    return datetime.now().strftime("%H:%M:%S")


def format_console_message(message: str, msg_type: str = "info") -> str:
    """
    Format a message for console output with timestamp and icon.
    
    Args:
        message: The message content
        msg_type: Type of message (info, command, output, error, success)
    
    Returns:
        Formatted message string with timestamp and icon
    """
    icons = {
        "command": "▶",
        "output": "  ",
        "error": "✗",
        "info": "ℹ",
        "success": "✓"
    }
    icon = icons.get(msg_type, "ℹ")
    timestamp = format_timestamp()
    return f"[{timestamp}] {icon} {message}"


def format_command_display(cmd_data: Dict[str, Any]) -> str:
    """
    Format a command for display in the script list.
    
    Args:
        cmd_data: Command dictionary with 'type' and 'params' keys
    
    Returns:
        Formatted string showing command type and parameters
    """
    cmd_type = cmd_data.get("type", "Unknown")
    params = cmd_data.get("params", {})
    
    if params:
        params_str = ", ".join(f"{k}={v}" for k, v in params.items())
        return f"{cmd_type} ({params_str})"
    return cmd_type


def format_window_title(title: str, max_length: int = 50) -> str:
    """
    Truncate window title to maximum length.
    
    Args:
        title: Full window title
        max_length: Maximum characters to display
    
    Returns:
        Truncated title
    """
    if len(title) <= max_length:
        return title
    return title[:max_length - 3] + "..."


def truncate_path(path: str, max_length: int = 30) -> str:
    """
    Truncate a file path for display.
    
    Args:
        path: Full file path
        max_length: Maximum characters to display
    
    Returns:
        Truncated path showing only filename
    """
    filename = path.split("/")[-1]
    if len(filename) <= max_length:
        return filename
    return filename[:max_length - 3] + "..."
