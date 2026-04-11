"""
Left Panel Component for GTT Page.
Contains daemon status, window list, quick actions, hotkeys, and macros.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QListWidget, QListWidgetItem, QGroupBox, QGridLayout
)
from qfluentwidgets import (
    SubtitleLabel, BodyLabel,
    PrimaryPushButton, PushButton, TransparentToolButton,
    ComboBox, CardWidget, IndeterminateProgressRing, FluentIcon
)
class LeftPanel(QWidget):
    """Left sidebar panel with GTT controls."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.init_ui()
    def init_ui(self) -> None:
        """Initialize left panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 10, 15)
        layout.setSpacing(12)
        self._create_daemon_status(layout)
        layout.addSpacing(10)
        self._create_window_list(layout)
        layout.addSpacing(10)
        self._create_hotkey_section(layout)
        layout.addSpacing(10)
        self._create_macros_section(layout)
        layout.addStretch()
    def _create_daemon_status(self, layout: QVBoxLayout) -> None:
        """Create daemon status section."""
        layout.addWidget(SubtitleLabel("GTT Daemon"))
        status_card = CardWidget()
        status_card.setStyleSheet(
            "CardWidget { background-color: #1a1f26; border: 1px solid #30363d; "
            "border-radius: 8px; padding: 12px; }"
        )
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
        layout.addWidget(self.start_gtt_btn)
        self.startup_progress = IndeterminateProgressRing()
        self.startup_progress.setVisible(False)
        layout.addWidget(self.startup_progress)
    def _create_window_list(self, layout: QVBoxLayout) -> None:
        """Create window list and quick actions."""
        layout.addWidget(SubtitleLabel("Windows"))
        refresh_btn = TransparentToolButton(FluentIcon.SYNC)
        refresh_btn.setToolTip("Refresh window list")
        refresh_btn.setMinimumHeight(32)
        refresh_btn.clicked.connect(self.window_refresh_clicked)
        layout.addWidget(refresh_btn)
        self.window_list_widget = QListWidget()
        self.window_list_widget.setStyleSheet(self._get_window_list_style())
        self.window_list_widget.setMaximumHeight(180)
        layout.addWidget(self.window_list_widget)
        actions_group = QGroupBox("Quick Actions")
        actions_group.setStyleSheet(self._get_group_style())
        actions_layout = QGridLayout(actions_group)
        actions_layout.setSpacing(6)
        self._create_window_action_buttons(actions_layout)
        layout.addWidget(actions_group)
    def _get_window_list_style(self) -> str:
        """Return window list stylesheet."""
        return """
            QListWidget { background-color: #1a1f26; border: 1px solid #30363d;
                border-radius: 8px; color: #e6edf3; font-size: 12px; }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background-color: #238636; }
        """
    def _get_group_style(self) -> str:
        """Return group box stylesheet."""
        return """
            QGroupBox { font-weight: bold; border: 1px solid #30363d;
                border-radius: 8px; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """
    def _create_window_action_buttons(self, layout: QGridLayout) -> None:
        """Create window action buttons."""
        self.focus_window_btn = PushButton("Focus")
        self.focus_window_btn.setMinimumHeight(32)
        layout.addWidget(self.focus_window_btn, 0, 0)
        self.close_window_btn = PushButton("Close")
        self.close_window_btn.setMinimumHeight(32)
        layout.addWidget(self.close_window_btn, 0, 1)
        self.minimize_window_btn = PushButton("Minimize")
        self.minimize_window_btn.setMinimumHeight(32)
        layout.addWidget(self.minimize_window_btn, 1, 0)
        self.maximize_window_btn = PushButton("Maximize")
        self.maximize_window_btn.setMinimumHeight(32)
        layout.addWidget(self.maximize_window_btn, 1, 1)
        self.unmaximize_window_btn = PushButton("Restore")
        self.unmaximize_window_btn.setMinimumHeight(32)
        layout.addWidget(self.unmaximize_window_btn, 2, 0)
        layout.setColumnStretch(2, 1)
    def _create_hotkey_section(self, layout: QVBoxLayout) -> None:
        """Create hotkey manager section."""
        layout.addWidget(SubtitleLabel("⌨️ Hotkeys"))
        self.hotkey_manager_btn = PrimaryPushButton("Manage Hotkeys")
        self.hotkey_manager_btn.setMinimumHeight(38)
        layout.addWidget(self.hotkey_manager_btn)
    def _create_macros_section(self, layout: QVBoxLayout) -> None:
        """Create macros section."""
        layout.addWidget(SubtitleLabel("Macros"))
        macros_scroll = QScrollArea()
        macros_scroll.setWidgetResizable(True)
        macros_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        macros_widget = QWidget()
        macros_layout = QGridLayout(macros_widget)
        macros_layout.setSpacing(6)
        self._create_macro_buttons(macros_layout)
        macros_scroll.setWidget(macros_widget)
        layout.addWidget(macros_scroll)
    def _create_macro_buttons(self, layout: QGridLayout) -> None:
        """Create macro buttons."""
        macros = [
            ("Focus Hyper", "focus_hyper"), ("Focus VS Code", "focus_vscode"),
            ("Focus Browser", "focus_browser"), ("Type Hello", "type_hello"),
            ("Copy/Paste", "copy_paste"), ("New Terminal", "new_terminal"),
            ("Screenshot", "screenshot"), ("Maximize", "maximize_window"),
            ("OCR Active", "ocr_active"), ("Clipboard", "clipboard_get"),
        ]
        for i, (name, macro_id) in enumerate(macros):
            btn = PushButton(name)
            btn.setMinimumHeight(32)
            btn.clicked.connect(lambda checked, mid=macro_id: self.macro_clicked(mid))
            layout.addWidget(btn, i // 2, i % 2)
        layout.setRowStretch((len(macros) // 2) + 1, 1)
    # Signal handlers to be connected by parent
    def window_refresh_clicked(self) -> None:
        """Handle window refresh button click."""
        if hasattr(self.parent(), 'refresh_windows'):
            self.parent().refresh_windows()
    def macro_clicked(self, macro_id: str) -> None:
        """Handle macro button click."""
        if hasattr(self.parent(), 'execute_macro'):
            self.parent().execute_macro(macro_id)
