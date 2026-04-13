"""
Voice Pipeline Orchestrator
==========================
Unified pipeline: ASR → Groq Post-Process → Translation → Voice AI/Dictation → TTS

Flow:
    [Audio] → [ASR] → [Groq Post-Process] → [Translate? via Groq] → [Voice AI via OmniProxy] → [TTS] → [Output]
    [Audio] → [ASR] → [Groq Post-Process] → [Translate? via Groq] → [Dictation via OmniProxy] → [Wbind] → [Typed Output]
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..llm import translate_text, process_voice_prompt
from ..languages import get_tts_languages
from ..llm_manager import LLMManager

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result from voice pipeline"""

    success: bool
    transcribed_text: str  # Raw ASR output
    detected_language: str  # Language detected by ASR
    translated_text: str  # After translation (if any)
    processed_text: str  # After Voice AI or Dictation processing
    output_text: str  # Final text for TTS or Wbind
    error: Optional[str] = None


class VoicePipeline:
    """
    Unified voice pipeline orchestrator.

    Coordinates: ASR → Groq Post-Process → Translation → Voice AI/Dictation → TTS/Wbind
    """

    def __init__(self, settings_manager):
        self.settings = settings_manager
        self.conversation_history: List[Dict] = []
        # Initialize Groq LLM manager for post-processing
        self.llm_manager = LLMManager(settings_manager)

    def reset_conversation(self):
        """Clear conversation history for new chat"""
        self.conversation_history = []

    async def process_voice_ai(
        self,
        audio_data,  # numpy array from ASR
        detected_language: str,
        target_language: str,
        tts_model: str,
        verbosity: str = "balanced",
        use_tools: bool = True,  # Enable TermPipe tools
    ) -> PipelineResult:
        """
        Full Voice AI pipeline:
        ASR output → Groq Post-Process → Translate if needed → Voice AI → TTS

        Returns text to be spoken by TTS
        """
        try:
            if not target_language:
                target_language = detected_language

            # Step 1: Groq post-processing to clean up ASR transcription
            cleaned_text = self.llm_manager.process_dictation(audio_data)

            # Step 2: Translate if needed
            if detected_language != target_language:
                translated = await translate_text(
                    cleaned_text,
                    source_lang=detected_language,
                    target_lang=target_language,
                )
            else:
                translated = cleaned_text

            # Step 3: Voice AI processing via OmniProxy
            processed = await process_voice_prompt(
                user_input=translated,
                conversation_history=self.conversation_history,
                target_language=target_language,
                mode="voice_ai",
                verbosity=verbosity,
                use_tools=use_tools,
            )

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": translated})
            self.conversation_history.append(
                {"role": "assistant", "content": processed}
            )

            return PipelineResult(
                success=True,
                transcribed_text=audio_data,
                detected_language=detected_language,
                translated_text=translated,
                processed_text=processed,
                output_text=processed,  # Same for voice AI
            )

        except Exception as e:
            logger.error(f"Voice AI pipeline error: {e}")
            return PipelineResult(
                success=False,
                transcribed_text=audio_data,
                detected_language=detected_language,
                translated_text="",
                processed_text="",
                output_text="",
                error=str(e),
            )

    async def process_dictation(
        self,
        audio_data: str,  # Text from ASR
        detected_language: str,
        target_language: str,
    ) -> PipelineResult:
        """
        Dictation pipeline:
        ASR output → Groq Post-Process → Translate if needed → Dictation (clean up) → Wbind

        Returns text to be typed via Wbind
        """
        try:
            if not target_language:
                target_language = detected_language

            # Step 1: Groq post-processing to clean up ASR transcription
            cleaned_text = self.llm_manager.process_dictation(audio_data)

            # Step 2: Translate if needed
            if detected_language != target_language:
                translated = await translate_text(
                    cleaned_text,
                    source_lang=detected_language,
                    target_lang=target_language,
                )
            else:
                translated = cleaned_text

            # Step 3: OmniProxy dictation processing (additional cleanup/formatting)
            processed = await process_voice_prompt(
                user_input=translated,
                conversation_history=[],  # No history for dictation
                target_language=target_language,
                mode="dictation",
            )

            return PipelineResult(
                success=True,
                transcribed_text=audio_data,
                detected_language=detected_language,
                translated_text=translated,
                processed_text=processed,
                output_text=processed,  # Text to type via Wbind
            )

        except Exception as e:
            logger.error(f"Dictation pipeline error: {e}")
            return PipelineResult(
                success=False,
                transcribed_text=audio_data,
                detected_language=detected_language,
                translated_text="",
                processed_text="",
                output_text="",
                error=str(e),
            )

    def get_supported_target_languages(self, tts_model: str) -> Dict[str, str]:
        """Get target languages supported by current TTS model"""
        return get_tts_languages(tts_model)


# Singleton
_pipeline: Optional[VoicePipeline] = None


def get_voice_pipeline(settings_manager) -> VoicePipeline:
    """Get singleton pipeline instance"""
    global _pipeline
    if _pipeline is None:
        _pipeline = VoicePipeline(settings_manager)
    return _pipeline
