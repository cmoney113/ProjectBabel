"""
Voice AI Service
High-level orchestration of the ASR -> LLM -> TTS pipeline
Provides a single entry point for voice interactions
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from enum import Enum

from src.conversation_context import ConversationContextManager

logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """Voice processing modes"""
    VOICE_AI = "voice_ai"  # Full conversation mode
    DICTATION = "dictation"  # Dictation with text injection


@dataclass
class VoiceAIRequest:
    """Request to the Voice AI service"""
    audio_data: Any  # numpy array
    mode: ProcessingMode = ProcessingMode.VOICE_AI
    target_language: Optional[str] = None
    translation_enabled: bool = False
    verbosity: str = "balanced"
    tts_model: str = "sopranotts"
    tts_voice: Optional[str] = None
    streaming: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VoiceAIResponse:
    """Response from the Voice AI service"""
    transcription: str
    response: str
    detected_language: str = "en"
    confidence: float = 0.0
    audio_played: bool = False
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class VoiceAIService:
    """
    High-level service for voice AI interactions.

    Orchestrates the complete pipeline:
    1. ASR: Audio -> Transcription (+ language detection)
    2. Translation (optional): Transcription -> Target language
    3. LLM: Transcription -> Response
    4. TTS: Response -> Audio

    Features:
    - Single entry point for UI layer
    - ConversationContextManager integration
    - Mode-aware processing (Voice AI vs Dictation)
    - Automatic language detection
    - Configurable verbosity
    """

    def __init__(
        self,
        voice_processor,
        llm_manager,
        tts_manager,
        settings_manager,
        conversation_context: ConversationContextManager = None,
    ):
        """
        Initialize VoiceAIService.

        Args:
            voice_processor: ASR processor instance
            llm_manager: LLM manager instance
            tts_manager: TTS manager instance
            settings_manager: Settings manager instance
            conversation_context: Optional ConversationContextManager (created if None)
        """
        self.voice_processor = voice_processor
        self.llm_manager = llm_manager
        self.tts_manager = tts_manager
        self.settings_manager = settings_manager

        # Conversation context (SSOT for history)
        self.conversation_context = conversation_context or ConversationContextManager()

        # Callbacks for UI updates
        self._on_transcription: Optional[Callable[[str], None]] = None
        self._on_response: Optional[Callable[[str], None]] = None
        self._on_processing_start: Optional[Callable[[], None]] = None
        self._on_processing_end: Optional[Callable[[], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

        # Pipeline configuration
        self._pipeline = None
        self._init_pipeline()

    def _init_pipeline(self):
        """Initialize the voice pipeline if available"""
        try:
            from src.pipeline import get_voice_pipeline
            self._pipeline = get_voice_pipeline(self.settings_manager)
        except ImportError:
            logger.info("Voice pipeline not available, using fallback")

    def set_callbacks(
        self,
        on_transcription: Callable[[str], None] = None,
        on_response: Callable[[str], None] = None,
        on_processing_start: Callable[[], None] = None,
        on_processing_end: Callable[[], None] = None,
        on_error: Callable[[str], None] = None,
    ):
        """Set UI update callbacks"""
        self._on_transcription = on_transcription
        self._on_response = on_response
        self._on_processing_start = on_processing_start
        self._on_processing_end = on_processing_end
        self._on_error = on_error

    async def process(self, request: VoiceAIRequest) -> VoiceAIResponse:
        """
        Process a voice AI request through the complete pipeline.

        Args:
            request: VoiceAIRequest with audio and configuration

        Returns:
            VoiceAIResponse with transcription, response, and metadata
        """
        try:
            if self._on_processing_start:
                self._on_processing_start()

            # Step 1: ASR - Transcribe audio with language detection
            transcription_result = self.voice_processor.transcribe_with_language(
                request.audio_data
            )
            transcription = transcription_result.text
            detected_language = transcription_result.detected_language
            confidence = transcription_result.confidence or 0.0

            if self._on_transcription:
                self._on_transcription(transcription)

            # Check for empty transcription
            if not transcription or not transcription.strip():
                logger.warning("No speech detected in audio")
                return VoiceAIResponse(
                    transcription="",
                    response="",
                    detected_language=detected_language,
                    confidence=confidence,
                    success=False,
                    error="No speech detected",
                )

            # Step 2 & 3: Process based on mode
            if request.mode == ProcessingMode.DICTATION:
                response = await self._process_dictation(
                    transcription, detected_language, request
                )
            else:
                response = await self._process_voice_ai(
                    transcription, detected_language, request
                )

            if self._on_response:
                self._on_response(response)

            # Step 4: TTS - Speak response
            audio_played = False
            if request.mode == ProcessingMode.VOICE_AI and response:
                audio_played = self._speak_response(response, request)

            return VoiceAIResponse(
                transcription=transcription,
                response=response,
                detected_language=detected_language,
                confidence=confidence,
                audio_played=audio_played,
                success=True,
            )

        except Exception as e:
            logger.error(f"Voice AI processing error: {e}")
            if self._on_error:
                self._on_error(str(e))
            return VoiceAIResponse(
                transcription="",
                response="",
                success=False,
                error=str(e),
            )
        finally:
            if self._on_processing_end:
                self._on_processing_end()

    async def _process_dictation(
        self,
        transcription: str,
        detected_language: str,
        request: VoiceAIRequest,
    ) -> str:
        """Process dictation mode"""
        if self._pipeline:
            result = await self._pipeline.process_dictation(
                audio_data=transcription,
                detected_language=detected_language,
                target_language=request.target_language,
            )
            return result.output_text
        else:
            # Fallback
            return self.llm_manager.process_dictation(transcription)

    async def _process_voice_ai(
        self,
        transcription: str,
        detected_language: str,
        request: VoiceAIRequest,
    ) -> str:
        """Process voice AI mode"""
        # Get context from ConversationContextManager
        context_messages = self.conversation_context.get_context_for_llm()

        if self._pipeline:
            result = await self._pipeline.process_voice_ai(
                audio_data=transcription,
                detected_language=detected_language,
                target_language=request.target_language,
                tts_model=request.tts_model,
                verbosity=request.verbosity,
            )
            response = result.output_text
        else:
            # Fallback to LLM manager
            response = self.llm_manager.generate_response_with_context(
                transcription, context_messages
            )

        # Update conversation context
        self.conversation_context.add_message("user", transcription)
        self.conversation_context.add_message("assistant", response)

        return response

    def _speak_response(self, response: str, request: VoiceAIRequest) -> bool:
        """Speak response via TTS"""
        try:
            kwargs = {"streaming": request.streaming}

            if request.tts_voice:
                kwargs["voice"] = request.tts_voice

            self.tts_manager.speak(response, **kwargs)
            return True
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            return False

    # === Convenience Methods ===

    def process_voice_ai(
        self,
        audio_data: Any,
        target_language: str = None,
        tts_model: str = None,
        tts_voice: str = None,
        verbosity: str = "balanced",
    ) -> VoiceAIResponse:
        """
        Process audio in Voice AI mode (synchronous wrapper).

        Convenience method that creates a VoiceAIRequest and calls process().
        """
        request = VoiceAIRequest(
            audio_data=audio_data,
            mode=ProcessingMode.VOICE_AI,
            target_language=target_language,
            tts_model=tts_model or self.settings_manager.get("tts_model", "sopranotts"),
            tts_voice=tts_voice,
            verbosity=verbosity,
            streaming=self.settings_manager.get("tts_streaming", True),
        )

        # Run async process in event loop
        loop = self._get_event_loop()
        return loop.run_until_complete(self.process(request))

    def process_dictation(
        self,
        audio_data: Any,
        target_language: str = None,
    ) -> VoiceAIResponse:
        """
        Process audio in Dictation mode (synchronous wrapper).

        Convenience method that creates a VoiceAIRequest and calls process().
        """
        request = VoiceAIRequest(
            audio_data=audio_data,
            mode=ProcessingMode.DICTATION,
            target_language=target_language,
        )

        loop = self._get_event_loop()
        return loop.run_until_complete(self.process(request))

    def _get_event_loop(self):
        """Get or create async event loop"""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    # === Conversation Management ===

    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation_context.clear_conversation()

    def get_conversation_stats(self) -> dict:
        """Get conversation statistics"""
        return self.conversation_context.get_conversation_stats()

    def save_conversation(self, filepath: str):
        """Save conversation to file"""
        self.conversation_context.save_to_file(filepath)

    def load_conversation(self, filepath: str):
        """Load conversation from file"""
        self.conversation_context.load_from_file(filepath)

    # === Backward Compatibility ===

    @property
    def conversation_history(self) -> list:
        """Backward compatible property for conversation history"""
        return self.conversation_context.get_context_for_llm()

    @conversation_history.setter
    def conversation_history(self, messages: list):
        """Backward compatible setter for conversation history"""
        self.conversation_context.clear_conversation()
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role and content:
                self.conversation_context.add_message(role, content)
