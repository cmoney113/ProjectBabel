"""
GTT Page Package
Enterprise RPA window automation and macro execution interface.

This package modularizes the GTT (GreaterTouchTool) page into focused components:
- main: GTTPage class assembling all components
- panels: Left, center, and right layout panels
- components: Reusable UI components (console, script builder, NLP bar)
- services: Backend services (bus client, window manager)
- utils: Helper functions and formatters
- startup: GTT daemon startup thread
- ai_command: AI command generator dialog
- hotkey_manager: Hotkey management dialog
- *_ops: Mixin modules for GTTPage functionality

Architecture:
- Separation of concerns with dedicated modules for each feature
- Mixin-based composition for GTTPage functionality
- Reusable components that can be tested independently
- BusClient for kernclip-bus IPC integration
"""

from .main import GTTPage
from .startup import GTTStartupThread
from .ai_command import AICommandDialog
from .hotkey_manager import HotkeyManagerDialog
from .services.bus_client import BusClient

__all__ = [
    "GTTPage",
    "GTTStartupThread",
    "AICommandDialog",
    "HotkeyManagerDialog",
    "BusClient",
]
