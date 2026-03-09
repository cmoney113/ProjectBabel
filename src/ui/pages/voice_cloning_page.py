"""
Voice Cloning Page - Voice cloning interface with reference audio and generation controls
Supports both VibeVoice (.pt voice files) and Chatterbox FP16 (reference audio)
"""

import os
import shutil
import threading
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QListWidgetItem,
)
from qfluentwidgets import (
    SubtitleLabel,
    BodyLabel,
    PushButton,
    ComboBox,
    LineEdit,
    TextEdit,
    CardWidget,
    IndeterminateProgressRing,
    SpinBox,
    InfoBar,
    PrimaryPushButton,
    ListWidget,
)


class VoiceCloneWorker(QThread):
    """Worker thread for voice cloning generation"""

    finished = Signal(object)  # Audio data
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, tts_manager, text, model, voice_name=None, ref_audio_path=None):
        super().__init__()
        self.tts_manager = tts_manager
        self.text = text
        self.model = model
        self.voice_name = voice_name
        self.ref_audio_path = ref_audio_path

    def run(self):
        try:
            self.progress.emit(f"Generating voice with {self.model}...")

            # Use TTS manager to generate speech
            audio = self.tts_manager.generate_speech(
                self.text,
                voice_cloning_audio=self.ref_audio_path,
                voice=self.voice_name if self.model == "vibevoice" else None,
            )

            if len(audio) > 0:
                self.finished.emit(audio)
            else:
                self.error.emit("No audio generated")

        except Exception as e:
            self.error.emit(str(e))


class VoiceCloningPage(QWidget):
    """Voice cloning page with reference audio selection and generation controls"""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.cloned_audio_data = None
        self.cloned_audio_sample_rate = 24000
        self.current_voice_file = None

        # Get references to managers
        self.settings_manager = main_window.get_settings_manager()
        self.tts_manager = main_window.get_tts_manager()

        # Voice directories
        self.vibevoice_voices_dir = (
            Path.home()
            / "new-projects"
            / "voice_ai"
            / "models"
            / "VibeVoiceRealtime05b"
            / "voices"
            / "streaming_model"
        )

        self.init_ui()
        self.connect_signals()
        self.refresh_voice_list()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.setObjectName("voice_cloning_page")

        # Header
        header_layout = QHBoxLayout()
        title = SubtitleLabel("Voice Cloning")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # ========== TTS Model Selection Card ==========
        model_card = CardWidget()
        model_layout = QVBoxLayout(model_card)

        model_title = SubtitleLabel("TTS Model")
        model_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        model_layout.addWidget(model_title)

        model_select_layout = QHBoxLayout()
        model_select_layout.addWidget(BodyLabel("Model:"))
        self.clone_tts_combo = ComboBox()

        # Add models that support voice cloning
        tts_models = {
            "vibevoice": "VibeVoice Realtime (Voice Presets)",
            "chatterbox-fp16": "Chatterbox FP16 (Reference Audio)",
        }

        for model_id, model_name in tts_models.items():
            self.clone_tts_combo.addItem(model_name, userData=model_id)

        # Set current model from settings
        current_tts = self.settings_manager.get("tts_model", "vibevoice")
        index = self.clone_tts_combo.findData(current_tts)
        if index >= 0:
            self.clone_tts_combo.setCurrentIndex(index)

        model_select_layout.addWidget(self.clone_tts_combo)
        model_select_layout.addStretch()
        model_layout.addLayout(model_select_layout)

        # Model description
        self.model_description = BodyLabel(
            "VibeVoice uses pre-generated .pt voice preset files for instant cloning"
        )
        self.model_description.setStyleSheet(
            "color: #888; font-size: 11px; margin-top: 5px;"
        )
        model_layout.addWidget(self.model_description)

        layout.addWidget(model_card)

        # ========== VibeVoice Voice Selection Card ==========
        self.vibevoice_card = CardWidget()
        vv_layout = QVBoxLayout(self.vibevoice_card)

        vv_title = SubtitleLabel("VibeVoice Voice Presets")
        vv_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        vv_layout.addWidget(vv_title)

        vv_desc = BodyLabel(
            "Select from built-in voices or import custom .pt voice files"
        )
        vv_desc.setStyleSheet("color: #888; font-size: 11px;")
        vv_layout.addWidget(vv_desc)

        # Voice list
        vv_list_layout = QHBoxLayout()
        self.voice_list = ListWidget()
        self.voice_list.setMaximumHeight(120)
        vv_list_layout.addWidget(self.voice_list)
        vv_layout.addLayout(vv_list_layout)

        # Voice controls
        vv_controls_layout = QHBoxLayout()

        self.import_voice_btn = PushButton("Import .pt Voice")
        self.import_voice_btn.setToolTip("Import a custom .pt voice preset file")
        vv_controls_layout.addWidget(self.import_voice_btn)

        self.delete_voice_btn = PushButton("Delete Selected")
        self.delete_voice_btn.setToolTip("Delete the selected voice preset")
        vv_controls_layout.addWidget(self.delete_voice_btn)

        self.refresh_voices_btn = PushButton("Refresh")
        self.refresh_voices_btn.setToolTip("Refresh the voice list")
        vv_controls_layout.addWidget(self.refresh_voices_btn)

        vv_controls_layout.addStretch()
        vv_layout.addLayout(vv_controls_layout)

        # Voice info
        self.voice_info = BodyLabel("Select a voice to use for cloning")
        self.voice_info.setStyleSheet("color: #666; font-size: 11px;")
        vv_layout.addWidget(self.voice_info)

        layout.addWidget(self.vibevoice_card)

        # ========== Chatterbox Reference Audio Card ==========
        self.chatterbox_card = CardWidget()
        cb_layout = QVBoxLayout(self.chatterbox_card)

        cb_title = SubtitleLabel("Chatterbox Reference Audio")
        cb_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        cb_layout.addWidget(cb_title)

        cb_desc = BodyLabel(
            "Provide a reference audio file to clone your voice (WAV, MP3, FLAC)"
        )
        cb_desc.setStyleSheet("color: #888; font-size: 11px;")
        cb_layout.addWidget(cb_desc)

        # Reference audio selection
        ref_audio_layout = QHBoxLayout()
        ref_audio_layout.addWidget(BodyLabel("Reference Audio:"))
        self.ref_audio_path_edit = LineEdit()
        self.ref_audio_path_edit.setPlaceholderText("Path to reference audio file...")
        self.ref_audio_path_edit.setText(
            self.settings_manager.get("voice_cloning", {}).get(
                "reference_audio_path", ""
            )
        )
        ref_audio_layout.addWidget(self.ref_audio_path_edit)

        self.browse_ref_audio_btn = PushButton("Browse")
        self.browse_ref_audio_btn.setToolTip("Browse for reference audio file")
        ref_audio_layout.addWidget(self.browse_ref_audio_btn)
        ref_audio_layout.addStretch()
        cb_layout.addLayout(ref_audio_layout)

        # Audio preview info
        self.ref_audio_info = BodyLabel("No reference audio selected")
        self.ref_audio_info.setStyleSheet("color: #666; font-size: 11px;")
        cb_layout.addWidget(self.ref_audio_info)

        self.chatterbox_card.setVisible(False)  # Hidden by default
        layout.addWidget(self.chatterbox_card)

        # ========== Text Input Card ==========
        text_card = CardWidget()
        text_layout = QVBoxLayout(text_card)

        text_title = SubtitleLabel("Text to Synthesize")
        text_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        text_layout.addWidget(text_title)

        # Text input
        self.clone_text_edit = TextEdit()
        self.clone_text_edit.setPlaceholderText(
            "Enter text to synthesize with cloned voice..."
        )
        self.clone_text_edit.setMaximumHeight(150)
        text_layout.addWidget(self.clone_text_edit)

        # Language selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(BodyLabel("Language:"))
        self.clone_language_combo = ComboBox()
        supported_langs = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
        }
        for lang_code, lang_name in supported_langs.items():
            self.clone_language_combo.addItem(lang_name, userData=lang_code)

        current_lang = self.settings_manager.get("tts_language", "en")
        index = self.clone_language_combo.findData(current_lang)
        if index >= 0:
            self.clone_language_combo.setCurrentIndex(index)

        lang_layout.addWidget(self.clone_language_combo)
        lang_layout.addStretch()
        text_layout.addLayout(lang_layout)

        layout.addWidget(text_card)

        # ========== Generation Controls Card ==========
        gen_card = CardWidget()
        gen_layout = QVBoxLayout(gen_card)

        gen_title = SubtitleLabel("Generate")
        gen_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        gen_layout.addWidget(gen_title)

        # Generate controls
        gen_controls_layout = QHBoxLayout()
        self.clone_generate_btn = PrimaryPushButton("Generate Cloned Voice")
        self.clone_generate_btn.setToolTip("Generate speech with the cloned voice")
        gen_controls_layout.addWidget(self.clone_generate_btn)

        self.clone_play_btn = PushButton("Play")
        self.clone_play_btn.setToolTip("Play the generated audio")
        self.clone_play_btn.setEnabled(False)
        gen_controls_layout.addWidget(self.clone_play_btn)

        self.clone_save_btn = PushButton("Save Audio")
        self.clone_save_btn.setToolTip("Save the generated audio to file")
        self.clone_save_btn.setEnabled(False)
        gen_controls_layout.addWidget(self.clone_save_btn)

        gen_controls_layout.addStretch()
        gen_layout.addLayout(gen_controls_layout)

        # Progress indicator
        self.clone_progress_ring = IndeterminateProgressRing()
        self.clone_progress_ring.setVisible(False)
        gen_layout.addWidget(
            self.clone_progress_ring, alignment=Qt.AlignmentFlag.AlignCenter
        )

        # Status label
        self.clone_status = BodyLabel("")
        self.clone_status.setStyleSheet("color: #888; font-size: 11px;")
        gen_layout.addWidget(self.clone_status)

        layout.addWidget(gen_card)

        layout.addStretch()

    def connect_signals(self):
        """Connect UI signals to handlers"""
        self.clone_tts_combo.currentIndexChanged.connect(self.on_model_changed)
        self.voice_list.currentItemChanged.connect(self.on_voice_selected)
        self.import_voice_btn.clicked.connect(self.import_voice_file)
        self.delete_voice_btn.clicked.connect(self.delete_selected_voice)
        self.refresh_voices_btn.clicked.connect(self.refresh_voice_list)
        self.browse_ref_audio_btn.clicked.connect(self.browse_reference_audio)
        self.clone_generate_btn.clicked.connect(self.generate_cloned_voice)
        self.clone_play_btn.clicked.connect(self.play_cloned_voice)
        self.clone_save_btn.clicked.connect(self.save_cloned_voice)

    def on_model_changed(self, index):
        """Handle model selection change"""
        model_id = self.clone_tts_combo.itemData(index)

        if model_id == "vibevoice":
            self.vibevoice_card.setVisible(True)
            self.chatterbox_card.setVisible(False)
            self.model_description.setText(
                "VibeVoice uses pre-generated .pt voice preset files for instant cloning"
            )
        else:
            self.vibevoice_card.setVisible(False)
            self.chatterbox_card.setVisible(True)
            self.model_description.setText(
                "Chatterbox uses reference audio to generate a cloned voice"
            )

        # Save selection
        self.settings_manager.set("tts_model", model_id)
        self.settings_manager.save_settings()

    def refresh_voice_list(self):
        """Refresh the list of available VibeVoice voices"""
        self.voice_list.clear()

        # Ensure directory exists
        if not self.vibevoice_voices_dir.exists():
            # Try alternative path
            alt_path = (
                Path.home()
                / "new-projects"
                / "voice_ai"
                / "models"
                / "VibeVoiceRealtime05b"
                / "voices"
            )
            if alt_path.exists():
                self.vibevoice_voices_dir = alt_path
            else:
                self.voice_info.setText(
                    f"Voices directory not found: {self.vibevoice_voices_dir}"
                )
                return

        # Load voice files
        voice_files = []
        for pt_path in self.vibevoice_voices_dir.rglob("*.pt"):
            voice_files.append(pt_path.stem)

        # Sort and add to list
        voice_files.sort()
        for voice_name in voice_files:
            self.voice_list.addItem(voice_name)

        self.voice_info.setText(f"Found {len(voice_files)} voice presets")

        # Select default voice
        if voice_files:
            default_voice = self.settings_manager.get("vibevoice_voice", "Carter")
            items = self.voice_list.findItems(default_voice, Qt.MatchFlag.MatchExactly)
            if items:
                self.voice_list.setCurrentItem(items[0])
            elif voice_files:
                self.voice_list.setCurrentRow(0)

    def on_voice_selected(self, current, previous):
        """Handle voice selection"""
        if current:
            voice_name = current.text()
            self.settings_manager.set("vibevoice_voice", voice_name)
            self.settings_manager.save_settings()
            self.voice_info.setText(f"Selected voice: {voice_name}")

    def import_voice_file(self):
        """Import a custom .pt voice file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Voice File",
            str(Path.home()),
            "Voice Files (*.pt);;All Files (*)",
        )

        if file_path:
            source = Path(file_path)
            voice_name = source.stem

            # Check if voice already exists
            dest_path = self.vibevoice_voices_dir / f"{voice_name}.pt"
            if dest_path.exists():
                InfoBar.warning(
                    "Voice Exists",
                    f"Voice '{voice_name}' already exists",
                    parent=self,
                    duration=2000,
                )
                return

            # Create directory if needed
            self.vibevoice_voices_dir.mkdir(parents=True, exist_ok=True)

            # Copy file
            try:
                shutil.copy2(source, dest_path)
                InfoBar.success(
                    "Voice Imported",
                    f"Successfully imported '{voice_name}'",
                    parent=self,
                    duration=2000,
                )
                self.refresh_voice_list()
            except Exception as e:
                InfoBar.error(
                    "Import Failed",
                    f"Failed to import voice: {str(e)}",
                    parent=self,
                    duration=3000,
                )

    def delete_selected_voice(self):
        """Delete the selected voice preset"""
        current_item = self.voice_list.currentItem()
        if not current_item:
            InfoBar.warning(
                "No Selection",
                "Please select a voice to delete",
                parent=self,
                duration=2000,
            )
            return

        voice_name = current_item.text()

        # Don't allow deleting built-in voices
        protected_voices = ["Carter", "Emma", "Davis", "Frank", "Grace", "Mike"]
        if voice_name in protected_voices:
            InfoBar.warning(
                "Protected Voice",
                f"Cannot delete built-in voice '{voice_name}'",
                parent=self,
                duration=2000,
            )
            return

        # Find and delete the file
        for pt_path in self.vibevoice_voices_dir.rglob(f"{voice_name}.pt"):
            try:
                pt_path.unlink()
                InfoBar.success(
                    "Voice Deleted",
                    f"Successfully deleted '{voice_name}'",
                    parent=self,
                    duration=2000,
                )
                self.refresh_voice_list()
            except Exception as e:
                InfoBar.error(
                    "Delete Failed",
                    f"Failed to delete voice: {str(e)}",
                    parent=self,
                    duration=3000,
                )
            return

        InfoBar.error(
            "Not Found",
            f"Voice file not found for '{voice_name}'",
            parent=self,
            duration=2000,
        )

    def browse_reference_audio(self):
        """Browse for reference audio file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Reference Audio",
            str(Path.home()),
            "Audio Files (*.wav *.mp3 *.flac *.ogg);;All Files (*)",
        )

        if file_path:
            self.ref_audio_path_edit.setText(file_path)
            self.ref_audio_info.setText(f"Selected: {Path(file_path).name}")

            # Save to settings
            voice_cloning = self.settings_manager.get("voice_cloning", {})
            voice_cloning["reference_audio_path"] = file_path
            self.settings_manager.set("voice_cloning", voice_cloning)
            self.settings_manager.save_settings()

    def generate_cloned_voice(self):
        """Generate cloned voice"""
        text = self.clone_text_edit.toPlainText().strip()
        if not text:
            InfoBar.warning(
                "No Text", "Please enter text to synthesize", parent=self, duration=2000
            )
            return

        model_id = self.clone_tts_combo.currentData()

        # Get voice/reference based on model
        voice_name = None
        ref_audio_path = None

        if model_id == "vibevoice":
            current_item = self.voice_list.currentItem()
            if not current_item:
                InfoBar.warning(
                    "No Voice Selected",
                    "Please select a voice preset",
                    parent=self,
                    duration=2000,
                )
                return
            voice_name = current_item.text()
        else:
            ref_audio_path = self.ref_audio_path_edit.text()
            if not ref_audio_path or not Path(ref_audio_path).exists():
                InfoBar.warning(
                    "No Reference Audio",
                    "Please select a reference audio file",
                    parent=self,
                    duration=2000,
                )
                return

        # Update UI
        self.clone_generate_btn.setEnabled(False)
        self.clone_play_btn.setEnabled(False)
        self.clone_save_btn.setEnabled(False)
        self.clone_progress_ring.setVisible(True)
        self.clone_status.setText(f"Generating with {model_id}...")

        # Get language
        language = self.clone_language_combo.currentData()

        # Start generation in thread
        self.worker = VoiceCloneWorker(
            self.tts_manager,
            text,
            model_id,
            voice_name=voice_name,
            ref_audio_path=ref_audio_path,
        )
        self.worker.progress.connect(self.on_generation_progress)
        self.worker.finished.connect(self.on_generation_complete)
        self.worker.error.connect(self.on_generation_error)
        self.worker.start()

    def on_generation_progress(self, message):
        """Handle generation progress"""
        self.clone_status.setText(message)

    def on_generation_complete(self, audio_data):
        """Handle generation complete"""
        self.cloned_audio_data = audio_data
        self.cloned_audio_sample_rate = 24000

        # Update UI
        self.clone_generate_btn.setEnabled(True)
        self.clone_play_btn.setEnabled(True)
        self.clone_save_btn.setEnabled(True)
        self.clone_progress_ring.setVisible(False)
        self.clone_status.setText(f"Generated {len(audio_data)} samples")

        InfoBar.success(
            "Generation Complete",
            "Voice cloned successfully",
            parent=self,
            duration=2000,
        )

    def on_generation_error(self, error_message):
        """Handle generation error"""
        # Update UI
        self.clone_generate_btn.setEnabled(True)
        self.clone_progress_ring.setVisible(False)
        self.clone_status.setText(f"Error: {error_message}")

        InfoBar.error("Generation Failed", error_message, parent=self, duration=3000)

    def play_cloned_voice(self):
        """Play cloned voice"""
        if self.cloned_audio_data is not None and len(self.cloned_audio_data) > 0:
            self.clone_status.setText("Playing...")
            self.tts_manager.play_audio(
                self.cloned_audio_data, self.cloned_audio_sample_rate
            )
            self.clone_status.setText("Playback complete")
        else:
            InfoBar.warning(
                "No Audio",
                "No audio to play. Generate first.",
                parent=self,
                duration=2000,
            )

    def save_cloned_voice(self):
        """Save cloned voice"""
        if self.cloned_audio_data is None or len(self.cloned_audio_data) == 0:
            InfoBar.warning(
                "No Audio",
                "No audio to save. Generate first.",
                parent=self,
                duration=2000,
            )
            return

        # Get output directory
        output_dir = Path(
            self.settings_manager.get(
                "tts_output_dir", str(Path.home() / "Documents" / "babel" / "outputs")
            )
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get filename
        voice_name = "cloned"
        current_item = self.voice_list.currentItem()
        if current_item:
            voice_name = current_item.text()

        # Find next counter
        counter = 0
        while True:
            filename = f"cloned_{voice_name}_{counter:04d}.wav"
            if not (output_dir / filename).exists():
                break
            counter += 1

        file_path = output_dir / filename

        # Save
        import soundfile as sf

        try:
            sf.write(file_path, self.cloned_audio_data, self.cloned_audio_sample_rate)
            InfoBar.success(
                "Audio Saved", f"Saved to {file_path.name}", parent=self, duration=2000
            )
        except Exception as e:
            InfoBar.error("Save Failed", str(e), parent=self, duration=3000)

    # === Public Methods for MainWindow compatibility ===

    def get_tts_model_combo(self):
        """Get TTS model combo for styling"""
        return self.clone_tts_combo

    def get_generate_button(self):
        """Get generate button for styling"""
        return self.clone_generate_btn

    def get_vibevoice_voice(self):
        """Get selected VibeVoice voice name"""
        current_item = self.voice_list.currentItem()
        if current_item:
            return current_item.text()
        return self.settings_manager.get("vibevoice_voice", "Carter")

    def get_reference_audio_path(self):
        """Get reference audio path for Chatterbox"""
        return self.ref_audio_path_edit.text()
