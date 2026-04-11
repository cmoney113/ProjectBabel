"""
Center Panel Component for GTT Page.
Contains tabbed interface with script builder, console, and hotkey preview.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QListWidget
from qfluentwidgets import BodyLabel
from ..components.console_output import ConsoleOutputPanel
from ..components.script_builder import ScriptBuilderPanel


class CenterPanel(QWidget):
    """Center tab panel with main GTT functionality."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize center panel with tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        tabs = QTabWidget()
        tabs.setStyleSheet(self._get_tab_style())
        tabs.setMinimumHeight(50)

        # Tab 1: Script Builder
        script_tab = QWidget()
        script_layout = QVBoxLayout(script_tab)
        script_layout.setContentsMargins(15, 15, 15, 15)
        script_layout.setSpacing(12)
        self.script_builder = ScriptBuilderPanel(self.parent())
        script_layout.addWidget(self.script_builder)
        tabs.addTab(script_tab, "📝 Script Builder")

        # Tab 2: Console
        console_tab = QWidget()
        console_layout = QVBoxLayout(console_tab)
        console_layout.setContentsMargins(15, 15, 15, 15)
        console_layout.setSpacing(12)
        self.console_panel = ConsoleOutputPanel(self.parent())
        console_layout.addWidget(self.console_panel)
        tabs.addTab(console_tab, "📋 Console Output")

        # Tab 3: Hotkey Preview
        hotkey_tab = QWidget()
        hotkey_layout = QVBoxLayout(hotkey_tab)
        hotkey_layout.setContentsMargins(15, 15, 15, 15)
        hotkey_layout.setSpacing(12)
        self._create_hotkey_tab(hotkey_layout)
        tabs.addTab(hotkey_tab, "⌨️ Hotkey Manager")
        layout.addWidget(tabs)

    def _get_tab_style(self) -> str:
        """Return tab widget stylesheet."""
        return """
            QTabWidget::pane { border: none; background-color: transparent; }
            QTabBar::tab { background-color: #1a1f26; color: #8b949e;
                padding: 10px 20px; margin-right: 2px;
                border-top-left-radius: 8px; border-top-right-radius: 8px; }
            QTabBar::tab:selected { background-color: #238636; color: white; }
            QTabBar::tab:hover { background-color: #21262d; }
        """

    def _create_hotkey_tab(self, layout: QVBoxLayout) -> None:
        """Create hotkey tab content."""
        info = BodyLabel("Use the Hotkey Manager button in the left sidebar to manage hotkeys.")
        info.setStyleSheet("color: #8b949e; font-size: 13px;")
        layout.addWidget(info)
        self.hotkey_preview = QListWidget()
        self.hotkey_preview.setStyleSheet(
            "QListWidget { background-color: #1a1f26; border: 1px solid #30363d; "
            "border-radius: 8px; color: #e6edf3; font-size: 13px; }"
        )
        layout.addWidget(self.hotkey_preview)

    def get_script_builder(self) -> ScriptBuilderPanel:
        """Get script builder panel reference."""
        return self.script_builder

    def get_console_panel(self) -> ConsoleOutputPanel:
        """Get console panel reference."""
        return self.console_panel
