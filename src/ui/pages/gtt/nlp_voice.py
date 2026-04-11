"""
GTT Page NLP and Voice Mixin.
Provides NLP command and voice control methods for GTTPage.
"""

import requests
from PySide6.QtCore import QTimer
from qfluentwidgets import InfoBar


class NLPVoiceMixin:
    """Mixin for NLP and voice control operations."""

    def send_nlp_command(self) -> None:
        """Send NLP command to CLIProxy."""
        nlp_text = self.right_panel.nlp_input.text().strip()
        if not nlp_text:
            InfoBar.warning("Empty Input", "Please enter a command", parent=self, duration=2000)
            return
        self.right_panel.history_list.addItem(f"📝 {nlp_text}")
        self.right_panel.set_nlp_progress(True)
        try:
            response = requests.post(
                f"{self.cliproxy_url}/v1/chat/completions",
                json={"model": "qwen3-coder-plus", "messages": [
                    {"role": "system", "content": "You are a GTT command generator. Output ONLY the gtt command."},
                    {"role": "user", "content": nlp_text}
                ]},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                gtt_cmd = data["choices"][0]["message"]["content"].strip()
                self.center_panel.console_panel.append(f"NLP → {gtt_cmd}", "command")
                self.execute_parsed_command(gtt_cmd)
                InfoBar.success("NLP Success", f"Executed: {gtt_cmd}", parent=self, duration=2000)
            else:
                InfoBar.error("NLP Error", f"CLIProxy error: {response.status_code}", parent=self, duration=3000)
        except Exception as e:
            InfoBar.error("NLP Error", str(e), parent=self, duration=3000)
        finally:
            self.right_panel.set_nlp_progress(False)

    def execute_parsed_command(self, command: str) -> None:
        """Execute parsed GTT command."""
        if command.startswith("gtt "):
            command = command[4:]
        parts = command.split()
        if parts:
            self.execute_gtt_command(["gtt"] + parts)

    def start_voice_command(self) -> None:
        """Start voice command recording."""
        self.right_panel.set_voice_status("Listening...", "#4A90E2")
        self.right_panel.voice_input_btn.setEnabled(False)
        try:
            success = self.voice_processor.start_recording()
            if success:
                InfoBar.info("Listening", "Speak your GTT command...", parent=self, duration=1000)
                QTimer.singleShot(5000, self.process_voice_command)
            else:
                self.reset_voice_state()
                InfoBar.error("Error", "Failed to start recording", parent=self, duration=2000)
        except Exception as e:
            self.reset_voice_state()
            InfoBar.error("Error", str(e), parent=self, duration=3000)

    def process_voice_command(self) -> None:
        """Process recorded voice command."""
        try:
            audio_data = self.voice_processor.stop_recording()
            if audio_data:
                transcription = self.voice_processor.transcribe_audio(audio_data)
                if transcription:
                    self.right_panel.set_voice_status(f"Heard: '{transcription}'")
                    self.right_panel.nlp_input.setText(transcription)
                    QTimer.singleShot(1000, self.send_nlp_command)
                else:
                    self.reset_voice_state()
                    InfoBar.warning("Transcription Failed", "Could not transcribe", parent=self, duration=2000)
            else:
                self.reset_voice_state()
                InfoBar.warning("No Audio", "No voice detected", parent=self, duration=2000)
        except Exception as e:
            self.reset_voice_state()
            InfoBar.error("Error", str(e), parent=self, duration=3000)

    def reset_voice_state(self) -> None:
        """Reset voice UI to ready state."""
        self.right_panel.set_voice_status("Ready")
        self.right_panel.voice_input_btn.setEnabled(True)
