"""
UI Handlers
Handles UI toggle and setting changes
"""

import logging
from PySide6.QtCore import QObject

logger = logging.getLogger(__name__)


class UIHandlers(QObject):
    """Handles UI toggle and setting changes"""

    def __init__(
        self,
        state_manager,
        settings_manager,
        waveform_widget=None,
        parent=None,
    ):
        super().__init__(parent)
        self.state_manager = state_manager
        self.settings_manager = settings_manager
        self.waveform_widget = waveform_widget

    def on_sensitivity_changed(self, sensitivity: str):
        """
        Handle sensitivity selection change

        Args:
            sensitivity: Sensitivity level (Low, Medium, High)
        """
        self.state_manager.update(sensitivity=sensitivity)
        self.settings_manager.set("sensitivity", sensitivity)

        if self.waveform_widget:
            self.waveform_widget.set_sensitivity(sensitivity)

        logger.info(f"Sensitivity changed to: {sensitivity}")

    def on_auto_vad_toggled(self, checked: bool):
        """
        Handle Auto VAD toggle

        Args:
            checked: Whether Auto VAD is enabled
        """
        self.state_manager.update(auto_vad_enabled=checked)
        self.settings_manager.set("auto_vad_enabled", checked)

        if checked:
            logger.info("Auto VAD trigger enabled")
        else:
            logger.info("Manual trigger enabled")

    def on_verbosity_changed(self, verbosity: str):
        """
        Handle verbosity selection change

        Args:
            verbosity: Verbosity level (concise, balanced, detailed)
        """
        self.state_manager.update(verbosity=verbosity)
        self.settings_manager.set("verbosity", verbosity)
        logger.info(f"Verbosity changed to: {verbosity}")

    def on_translation_toggled(self, enabled: bool):
        """
        Handle translation toggle

        Args:
            enabled: Whether translation is enabled
        """
        self.state_manager.update(translation_enabled=enabled)
        self.settings_manager.set("translation_enabled", enabled)
        logger.info(f"Translation {'enabled' if enabled else 'disabled'}")

    def on_target_language_changed(self, lang_code: str):
        """
        Handle target language selection change

        Args:
            lang_code: Language code (e.g., 'en', 'es')
        """
        self.state_manager.update(target_language=lang_code)
        self.settings_manager.set("target_language", lang_code)
        logger.info(f"Target language changed to: {lang_code}")

    def on_mode_toggled(self, is_dictation_mode: bool):
        """
        Handle mode toggle between Voice AI and Dictation

        Args:
            is_dictation_mode: Whether dictation mode is enabled
        """
        self.state_manager.update(is_dictation_mode=is_dictation_mode)
        logger.info(
            f"Mode changed to: {'Dictation' if is_dictation_mode else 'Voice AI'}"
        )

    def on_window_selected(self, window_id: str):
        """
        Handle window selection change for dictation mode

        Args:
            window_id: Selected window ID
        """
        self.state_manager.update(selected_window_id=window_id)
        logger.info(f"Dictation window selected: {window_id}")

    def on_custom_text_toggled(self, enabled: bool):
        """
        Handle custom text mode toggle

        Args:
            enabled: Whether custom text mode is enabled
        """
        self.state_manager.update(custom_text_enabled=enabled)
        logger.info(f"Custom text mode {'enabled' if enabled else 'disabled'}")
