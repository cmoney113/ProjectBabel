#!/usr/bin/env python3
"""
Voice AI System Tray Application
Provides quick access to voice AI controls without opening the main window.
"""

import sys
import os
import subprocess
import json
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QWidget
from PySide6.QtGui import QIcon, QAction, QActionGroup, QPixmap, QColor
from PySide6.QtCore import QTimer, Signal, QObject

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model_registry import ModelRegistry
from src.tts_manager import TTSManager
from src.voice_processor import VoiceProcessor
from src.settings_manager import SettingsManager


class TrayApp(QObject):
    """System tray application for Voice AI controls"""

    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Initialize managers with dependencies
        self.settings_manager = SettingsManager()
        self.tts_manager = TTSManager(self.settings_manager)
        self.voice_processor = VoiceProcessor(self.settings_manager)

        # Create tray icon
        self.tray_icon = QSystemTrayIcon()
        self.create_icon()

        # Create menu
        self.menu = QMenu()
        self.create_menu()

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

    def create_icon(self):
        """Create a simple icon for the tray"""
        # Use the voice AI icon
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "assets", "voiceai_icon.png"
        )
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Fallback to simple icon if file not found
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor("#4CAF50"))  # Green color
            self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("Voice AI Assistant")

    def create_menu(self):
        """Create the system tray menu"""

        # ASR Model Submenu
        asr_menu = self.menu.addMenu("ASR Model")
        self.create_asr_model_menu(asr_menu)

        # TTS Model Submenu
        tts_menu = self.menu.addMenu("TTS Model")
        self.create_tts_model_menu(tts_menu)

        # Mode Selection Submenu
        mode_menu = self.menu.addMenu("Mode")
        self.create_mode_menu(mode_menu)

        # Window Selection Submenu
        window_menu = self.menu.addMenu("Target Window")
        self.create_window_menu(window_menu)

        self.menu.addSeparator()

        # Start Listening Action
        start_listening_action = QAction("Start Listening", self.menu)
        start_listening_action.triggered.connect(self.start_listening)
        self.menu.addAction(start_listening_action)

        self.menu.addSeparator()

        # Quit Action
        quit_action = QAction("Quit", self.menu)
        quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(quit_action)

        # Update menu states
        self.update_menu_states()

    def create_asr_model_menu(self, parent_menu):
        """Create ASR model selection submenu"""
        self.asr_action_group = QActionGroup(self)
        self.asr_action_group.setExclusive(True)

        # Get available ASR models from registry
        for model_id, model_info in ModelRegistry.ASR_MODELS.items():
            action = QAction(model_info.display_name, parent_menu)
            action.setCheckable(True)
            action.setData(model_id)
            action.triggered.connect(self.on_asr_model_changed)
            self.asr_action_group.addAction(action)
            parent_menu.addAction(action)

    def create_tts_model_menu(self, parent_menu):
        """Create TTS model selection submenu"""
        self.tts_action_group = QActionGroup(self)
        self.tts_action_group.setExclusive(True)

        # Get available TTS models from registry
        for model_id, model_info in ModelRegistry.TTS_MODELS.items():
            action = QAction(model_info.display_name, parent_menu)
            action.setCheckable(True)
            action.setData(model_id)
            action.triggered.connect(self.on_tts_model_changed)
            self.tts_action_group.addAction(action)
            parent_menu.addAction(action)

    def create_mode_menu(self, parent_menu):
        """Create mode selection submenu"""
        self.mode_action_group = QActionGroup(self)
        self.mode_action_group.setExclusive(True)

        # Dictation Mode (default)
        dictation_action = QAction("Dictation", parent_menu)
        dictation_action.setCheckable(True)
        dictation_action.setData("dictation")
        dictation_action.triggered.connect(self.on_mode_changed)
        self.mode_action_group.addAction(dictation_action)
        parent_menu.addAction(dictation_action)

        # Voice AI Mode
        voice_ai_action = QAction("Voice AI", parent_menu)
        voice_ai_action.setCheckable(True)
        voice_ai_action.setData("voice_ai")
        voice_ai_action.triggered.connect(self.on_mode_changed)
        self.mode_action_group.addAction(voice_ai_action)
        parent_menu.addAction(voice_ai_action)

    def create_window_menu(self, parent_menu):
        """Create window selection submenu"""
        self.window_action_group = QActionGroup(self)
        self.window_action_group.setExclusive(True)

        # Default "Current Window" option
        current_window_action = QAction("Current Window", parent_menu)
        current_window_action.setCheckable(True)
        current_window_action.setData("current")
        current_window_action.triggered.connect(self.on_window_changed)
        self.window_action_group.addAction(current_window_action)
        parent_menu.addAction(current_window_action)

        # Add functionality to enumerate open windows
        try:
            windows = self.tts_manager.get_window_list()
            for window in windows:
                title = window.get("title", f"Window {window.get('id', 'unknown')}")
                wm_class = window.get("wm_class", "unknown")
                display_text = f"{title} ({wm_class})"

                window_action = QAction(display_text, parent_menu)
                window_action.setCheckable(True)
                window_action.setData(window.get("id"))
                window_action.triggered.connect(self.on_window_changed)
                self.window_action_group.addAction(window_action)
                parent_menu.addAction(window_action)
        except Exception as e:
            print(f"Failed to enumerate windows: {e}")

    def update_menu_states(self):
        """Update menu items to reflect current settings"""

        # Set current ASR model
        current_asr = self.voice_processor.get_current_asr_model()
        for action in self.asr_action_group.actions():
            if action.data() == current_asr:
                action.setChecked(True)
                break

        # Set current TTS model
        current_tts = self.tts_manager.get_current_tts_model()
        for action in self.tts_action_group.actions():
            if action.data() == current_tts:
                action.setChecked(True)
                break

        # Set current mode (default to Dictation)
        # TODO: Get actual current mode from settings
        dictation_action = self.mode_action_group.actions()[0]
        dictation_action.setChecked(True)

        # Set current window (default to Current Window)
        current_window_action = self.window_action_group.actions()[0]
        current_window_action.setChecked(True)

    def on_asr_model_changed(self):
        """Handle ASR model selection change"""
        action = self.sender()
        if isinstance(action, QAction) and action.isChecked():
            model_id = action.data()
            print(f"Switching ASR model to: {model_id}")
            self.voice_processor.switch_asr_model(model_id)

    def on_tts_model_changed(self):
        """Handle TTS model selection change"""
        action = self.sender()
        if isinstance(action, QAction) and action.isChecked():
            model_id = action.data()
            print(f"Switching TTS model to: {model_id}")
            self.tts_manager.set_current_tts_model(model_id)

    def on_mode_changed(self):
        """Handle mode selection change"""
        action = self.sender()
        if isinstance(action, QAction) and action.isChecked():
            mode = action.data()
            print(f"Switching mode to: {mode}")
            # TODO: Implement mode switching
            # This would need to integrate with the existing mode controls

    def start_listening(self):
        """Start voice listening"""
        print("Starting voice listening...")
        self.voice_processor.start_recording()

    def on_window_changed(self):
        """Handle window selection change"""
        action = self.sender()
        if isinstance(action, QAction) and action.isChecked():
            window_id = action.data()
            print(f"Setting target window to: {window_id}")

            if window_id == "current":
                # "Current Window" option - no need to focus
                print("Using current window")
            else:
                # Focus the selected window using gtt
                try:
                    window_id_int = int(window_id)
                    success = self.tts_manager.focus_window(window_id_int)
                    if success:
                        print(f"Successfully focused window {window_id_int}")
                    else:
                        print(f"Failed to focus window {window_id_int}")
                except ValueError:
                    print(f"Invalid window ID: {window_id}")

    def quit_app(self):
        """Quit the tray application"""
        self.app.quit()

    def run(self):
        """Run the tray application"""
        print("Voice AI Tray App started")
        print("Available in system tray - right-click to access controls")
        sys.exit(self.app.exec())


def main():
    """Main entry point for the tray application"""
    tray_app = TrayApp()
    tray_app.run()


if __name__ == "__main__":
    main()
