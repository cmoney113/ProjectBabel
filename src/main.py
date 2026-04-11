#!/usr/bin/env python3
"""
Canary Voice AI Assistant - Main Application Entry Point
Modern PySide6/Fluent UI Application with Modular Architecture

Features:
- Canary-1b-v2 ASR -> Groq openai/gpt-oss-120b -> NeuTTS-Nano pipeline
- Two modes: Voice AI Assistant and Dictation Mode
- Toggle between VAD auto-trigger and manual key press
- Dark navy theme with Fluent UI animations and transitions
- Real-time speech transcription and model response display
- Tavily web search integration for current events and comprehensive answers
- Context-aware conversation history with language detection and translation
- Configurable hotkey for manual activation
"""

import sys
import os
import atexit
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
from qfluentwidgets import setTheme, Theme

from src.ui.main_window import MainWindow
from src.http_client import close_http_client


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Canary Voice AI Assistant")
    app.setFont(QFont("Segoe UI", 10))

    # Set dark navy theme
    setTheme(Theme.DARK)
    app.setStyleSheet("""
        QMainWindow, FluentWindow {
            background-color: #0a0f1d;
        }
    """)

    def cleanup():
        print("Cleaning up resources...")
        try:
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(close_http_client())
            loop.close()
        except Exception as e:
            print(f"Cleanup error: {e}")

    app.aboutToQuit.connect(cleanup)
    atexit.register(cleanup)

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
