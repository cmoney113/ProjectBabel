"""
GTT Page Main Module.
Main GTTPage class that assembles all components into the complete page.
"""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QHBoxLayout
from .startup import GTTStartupThread
from .services.bus_client import BusClient
from .panels.left_panel import LeftPanel
from .panels.center_panel import CenterPanel
from .panels.right_panel import RightPanel
from .hotkey_manager import HotkeyManagerDialog
from .window_ops import WindowManagementMixin
from .macro_ops import MacroOperationsMixin
from .nlp_voice import NLPVoiceMixin
from .daemon_ops import DaemonManagementMixin
from .script_ops import ScriptExecutionMixin


class GTTPage(QWidget, WindowManagementMixin, MacroOperationsMixin,
              NLPVoiceMixin, DaemonManagementMixin, ScriptExecutionMixin):
    """GTT automation page with window management, macros, and NLP integration."""

    def __init__(self, main_window):
        super().__init__()
        self.setObjectName("GTTPage")
        self.main_window = main_window
        self.cliproxy_url = "http://localhost:7599"
        self.window_list = []
        self.gtt_running = False
        self.startup_thread = None
        self.bus = BusClient()
        self.settings_manager = main_window.get_settings_manager()
        self.voice_processor = main_window.get_voice_processor()
        self._init_ui()
        self._connect_signals()
        self.check_gtt_status()

    def _init_ui(self) -> None:
        """Initialize the main UI layout."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.left_panel = LeftPanel(self)
        main_layout.addWidget(self.left_panel)
        self.center_panel = CenterPanel(self)
        main_layout.addWidget(self.center_panel)
        self.right_panel = RightPanel(self)
        main_layout.addWidget(self.right_panel)

    def _connect_signals(self) -> None:
        """Connect UI signals and timers."""
        self.left_panel.hotkey_manager_btn.clicked.connect(self.open_hotkey_manager)
        self.center_panel.script_builder.window_list = self.window_list
        self.bus_refresh_timer = QTimer()
        self.bus_refresh_timer.timeout.connect(self.refresh_bus_status)
        self.bus_refresh_timer.start(5000)
        self.bus_message_timer = QTimer()
        self.bus_message_timer.timeout.connect(self.check_bus_messages)
        self.bus_message_timer.start(100)

    def refresh_bus_status(self) -> None:
        """Refresh bus status."""
        self.bus._check_availability()
        self.center_panel.console_panel.set_bus_status(self.bus.available)

    def check_bus_messages(self) -> None:
        """Check for bus messages."""
        if not self.bus.available:
            return

    def open_hotkey_manager(self) -> None:
        """Open hotkey manager dialog."""
        dialog = HotkeyManagerDialog(self)
        dialog.show()

    def get_settings_manager(self):
        """Get settings manager from main window."""
        return self.settings_manager

    def get_voice_processor(self):
        """Get voice processor from main window."""
        return self.voice_processor
