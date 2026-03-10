"""
Voice AI State Management
Centralized state for the Voice AI page - single source of truth
"""

from dataclasses import dataclass, field
from PySide6.QtCore import QObject, Signal


@dataclass
class VoiceAIState:
    """Immutable state container for Voice AI page"""

    # Model selections
    current_asr_model: str = "canary"
    current_tts_model: str = "kittentts"
    kittentts_voice: str = "Jasper"
    vibevoice_voice: str = "Carter"
    vibevoice_language: str = "en"

    # Recording state
    is_listening: bool = False
    is_processing: bool = False
    recording_start_time: float = 0.0
    sensitivity: str = "Medium"
    auto_vad_enabled: bool = False

    # Response settings
    verbosity: str = "balanced"  # concise, balanced, detailed
    translation_enabled: bool = False
    target_language: str = "en"

    # Mode settings
    is_dictation_mode: bool = False
    selected_window_id: str | None = None

    # Custom text mode
    custom_text_enabled: bool = False


class StateManager(QObject):
    """Manages Voice AI state with signal notifications for changes"""

    # State change signals
    state_changed = Signal(object)  # Emits VoiceAIState
    asr_model_changed = Signal(str)
    tts_model_changed = Signal(str)
    recording_state_changed = Signal(bool)  # is_listening
    processing_state_changed = Signal(bool)  # is_processing
    dictation_mode_changed = Signal(bool)
    translation_changed = Signal(bool)

    def __init__(self, settings_manager=None):
        super().__init__()
        self._state = VoiceAIState()
        self._settings_manager = settings_manager

    @property
    def state(self) -> VoiceAIState:
        """Get current state (read-only)"""
        return self._state

    def update(self, **kwargs):
        """Update state fields and emit change signals"""
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                old_value = getattr(self._state, key)
                setattr(self._state, key, value)

                # Emit specific signals for important changes
                self._emit_change_signal(key, value, old_value)

        self.state_changed.emit(self._state)

    def _emit_change_signal(self, key: str, value, old_value):
        """Emit specific change signal if applicable"""
        if key == "current_asr_model" and value != old_value:
            self.asr_model_changed.emit(value)
        elif key == "current_tts_model" and value != old_value:
            self.tts_model_changed.emit(value)
        elif key == "is_listening" and value != old_value:
            self.recording_state_changed.emit(value)
        elif key == "is_processing" and value != old_value:
            self.processing_state_changed.emit(value)
        elif key == "is_dictation_mode" and value != old_value:
            self.dictation_mode_changed.emit(value)
        elif key == "translation_enabled" and value != old_value:
            self.translation_changed.emit(value)

    # Convenience methods for common operations
    def start_listening(self):
        """Mark listening as started"""
        import time

        self.update(is_listening=True, recording_start_time=time.time())

    def stop_listening(self):
        """Mark listening as stopped"""
        self.update(is_listening=False, recording_start_time=0.0)

    def start_processing(self):
        """Mark processing as started"""
        self.update(is_processing=True)

    def stop_processing(self):
        """Mark processing as stopped"""
        self.update(is_processing=False)

    def get_elapsed_time(self) -> float:
        """Get elapsed recording time in seconds"""
        if self._state.recording_start_time > 0:
            import time

            return time.time() - self._state.recording_start_time
        return 0.0

    def load_from_settings(self):
        """Load state from settings manager"""
        if not self._settings_manager:
            return

        self.update(
            current_asr_model=self._settings_manager.get("asr_model", "canary"),
            current_tts_model=self._settings_manager.get("tts_model", "kittentts"),
            kittentts_voice=self._settings_manager.get("kittentts_voice", "Jasper"),
            vibevoice_voice=self._settings_manager.get("vibevoice_voice", "Carter"),
            vibevoice_language=self._settings_manager.get("vibevoice_language", "en"),
            sensitivity=self._settings_manager.get("sensitivity", "Medium"),
            verbosity=self._settings_manager.get("verbosity", "balanced"),
            translation_enabled=self._settings_manager.get("translation_enabled", False),
            target_language=self._settings_manager.get("target_language", "en"),
            auto_vad_enabled=self._settings_manager.get("auto_vad_enabled", False),
        )

    def save_to_settings(self):
        """Save current state to settings manager"""
        if not self._settings_manager:
            return

        self._settings_manager.set("asr_model", self._state.current_asr_model)
        self._settings_manager.set("tts_model", self._state.current_tts_model)
        self._settings_manager.set("kittentts_voice", self._state.kittentts_voice)
        self._settings_manager.set("vibevoice_voice", self._state.vibevoice_voice)
        self._settings_manager.set("vibevoice_language", self._state.vibevoice_language)
        self._settings_manager.set("sensitivity", self._state.sensitivity)
        self._settings_manager.set("verbosity", self._state.verbosity)
        self._settings_manager.set("translation_enabled", self._state.translation_enabled)
        self._settings_manager.set("target_language", self._state.target_language)
        self._settings_manager.set("auto_vad_enabled", self._state.auto_vad_enabled)
