#!/usr/bin/env python3
"""
Sovd: Canary 1B Daemon - Multilingual STT Listener with Profile Support

ARCHITECTURE: Enhanced VAD with Artifact Filtering & Smart Chunking + Profiles
- Audio accumulates continuously into buffer (up to 40s safety cap)
- VAD watches raw audio RMS levels
- When silence detected for X ms → grace period → user can re-activate by speaking
- Only processes after grace period expires (voice push-to-talk UX)
- Profile system for wake word → processing mode switching
- Profile-specific LLM prompts and output formatting
- Artifact filtering prevents filler words/punctuation from being typed
- Smart chunking handles utterances >40s by starting second thread at 85%
- Integrates with VAD gating engine for precise silence detection
"""

import json
import logging
import os
import queue
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
import traceback
from pathlib import Path

import numpy as np
import sounddevice as sd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from covd_cli import add_common_listening_args, add_profile_args, get_base_parser, add_transcribe_args
from inference.canary_1b_v2 import Canary1Bv2
from utils.config import ConfigManager
from utils.language_detector import auto_select_model
from utils.llm_client import LLMClient
from utils.profile_manager import ProfileManager
from utils.sound_player import SoundPlayer
from utils.telemetry import TelemetryCollector
from utils.text_processor import ProcessingResult, ProfileAwareTextProcessor
from utils.vad_gating import VADConfig
from utils.wbind_controller import WBindController
from utils.transcriber import Transcriber, DEFAULT_OUTPUT_DIR

logger = logging.getLogger("sovd")

class JSONBufferLogger:
    """Append-only JSON log for utterance records"""

    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize file with empty array if doesn't exist
        if not self.log_path.exists():
            self.log_path.write_text("[]")

    def append(self, record: dict):
        """Append a record to the JSON buffer"""
        try:
            # Read existing
            data = json.loads(self.log_path.read_text())

            # Append new record
            data.append(record)

            # Write back
            self.log_path.write_text(json.dumps(data, indent=2))

        except Exception as e:
            logger.error(f"Failed to write JSON buffer: {e}")


def transcribe_file_cli(args):
    """Handles transcription of a single audio file via CLI."""
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info(f"Starting single file transcription for: {args.scribe}")

    script_dir = Path(__file__).parent
    models_dir = script_dir / "models"
    audio_path = Path(args.scribe)
    
    # Determine model directory
    if getattr(args, 'auto', False):
        # Auto-detect language and select model
        model_dir, reason = auto_select_model(audio_path, verbose=args.verbose)
        logger.info(f"AUTO-MODE: {reason}")
    elif args.model == "flash":
        model_dir = models_dir / "canary-multi-flash-180m"
    else:
        model_dir = models_dir / "canary1b"

    logger.info(f"Using model: {model_dir}")

    try:
        logger.debug("Before initializing ConfigManager in transcribe_file_cli")
        config_manager = ConfigManager()
        logger.debug("After initializing ConfigManager in transcribe_file_cli")
        # Initialize Transcriber
        logger.debug("Before initializing Transcriber in transcribe_file_cli")
        transcriber = Transcriber(
            model_dir=model_dir,
            llm_config=config_manager.get_config(), # Pass global config for LLM
            verbose=args.verbose
        )
        logger.debug("After initializing Transcriber in transcribe_file_cli")

        output_dir = Path(os.path.expanduser(args.outpath)) if args.outpath else DEFAULT_OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True) # Ensure output directory exists

        output_path = transcriber.transcribe_audio_file(
            audio_file_path=audio_path,
            output_dir=output_dir,
            language=getattr(args, "lang", "en")
        )
        logger.info(f"Transcription complete. Output saved to: {output_path}")

    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during transcription: {e}")
        traceback.print_exc()
        sys.exit(1)

def run(args):
    # Setup Logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s")

    logger.info(
        "Starting sovd (Canary 1B) - Enhanced VAD with profiles, artifact filtering & smart chunking"
    )

    # Handle --list-profiles early (before full daemon start)
    if hasattr(args, "list_profiles") and args.list_profiles:
        config_manager = ConfigManager()
        pm = ProfileManager(config_manager)
        print(pm.get_profile_summary())
        sys.exit(0)

    # Shutdown flag for graceful exit
    shutdown_requested = False

    def signal_handler(signum, frame):
        nonlocal shutdown_requested
        sig_name = signal.Signals(signum).name
        logger.info(f"\n{'=' * 80}")
        logger.info(f"🛑 Received {sig_name} - Initiating graceful shutdown...")
        logger.info(f"{'=' * 80}")
        shutdown_requested = True

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Load Config
    config_manager = ConfigManager()
    config = config_manager.get_config()

    # CLI Overrides
    if args.no_llm:
        config.enable_llm = False
    if args.paste:
        config.typing_mode = "paste"
    if args.silence:
        config.silence_timeout_ms = int(args.silence * 1000)
    if args.wake:
        config.enable_wakeword = True
    if args.wake_new:
        config.wakeword_phrase = args.wake_new

    lang_hint = getattr(args, "lang", "auto")

    # Initialize Components
    sound = SoundPlayer(config_manager, verbose=args.verbose)
    telemetry = TelemetryCollector("canary-1b", config_manager)
    llm = LLMClient(config, verbose=args.verbose) if config.enable_llm else None
    wbind = WBindController(config_manager)

    # Initialize Profile Manager
    profile_manager = ProfileManager(config_manager)

    # Handle --profile CLI arg
    if hasattr(args, "profile") and args.profile:
        if profile_manager.switch_profile(args.profile):
            logger.info(f"🚀 Starting with profile: {args.profile}")
        else:
            logger.error(f"❌ Unknown profile: {args.profile}")
            logger.info(
                "Available profiles: " + ", ".join(profile_manager.profiles.keys())
            )
            sys.exit(1)
    else:
        logger.info(
            f"📋 Using default profile: {profile_manager.get_current_profile().name}"
        )

    # Handle --profile-status (after profile switch is applied)
    if hasattr(args, "profile_status") and args.profile_status:
        profile = profile_manager.get_current_profile()
        print(f"\n📋 Current Profile: {profile.name}")
        print(f"   Description: {profile.description}")
        print(f"   Output Format: {profile.output_format}")
        print(f"   Output Keys: {' + '.join(profile.output_keys)}")
        if profile.wake_words:
            print(f"   Wake Words: {', '.join(profile.wake_words[:5])}")
        sys.exit(0)

    # Initialize Profile-Aware Text Processor
    output_lock = threading.Lock()
    text_processor = ProfileAwareTextProcessor(
        profile_manager=profile_manager,
        llm_client=llm,
        rules=config.rules,
        output_lock=output_lock,
    )

    # JSON Buffer Logger
    json_buffer_path = Path.home() / ".vokoro-cli" / "utterance_buffer.json"
    json_logger = JSONBufferLogger(json_buffer_path)
    logger.info(f"JSON buffer: {json_buffer_path}")

    # Load ASR - Canary 1B (model loads in __init__)
    model_dir = Path(__file__).parent / "models" / "canary1b"
    load_start = time.time()
    try:
        asr = Canary1Bv2(model_dir, provider="cpu")
    except Exception as e:
        logger.error(f"Failed to load Canary 1B model: {e}")
        sys.exit(1)
    load_time = time.time() - load_start
    telemetry.log_model_load(load_time, "cpu")
    logger.info(f"✅ Canary 1B model loaded in {load_time:.2f}s")

    # Initialize VAD Gating Engine (event-driven architecture)
    vad_config = VADConfig(
        silence_timeout_ms=config.silence_timeout_ms,
        min_accumulated_text_length=2,  # Min chars before considering flush
        noise_threshold=0.05,
        vad_enabled=True,
        debug_mode=args.verbose,
    )

    class RealisticEnergyStateMachine:
        """
        Deterministic Energy-Based State Machine for VAD.

        States:
        - IDLE: No speech detected, buffer empty.
        - SPEECH: Energy detected, accumulating audio.
        - GRACE: Energy dropped, waiting for resume or timeout.

        Features:
        - Robust default threshold (0.015) to ignore noise.
        - "Peek" check: When entering GRACE, checks last 2s for sentence boundary.
          If found, flushes immediately (responsive).
          If not, waits for grace period (allows mid-thought pauses).
        """

        # Robust default - "generous/normal for any kind of speech"
        # Can be overridden by config.vad_threshold if set
        DEFAULT_THRESHOLD = 0.020

        def __init__(self, config, asr_model, lang_hint):
            self.config = config
            self.asr = asr_model
            self.lang_hint = lang_hint

            # Use configured threshold or default
            self.ENERGY_THRESHOLD = getattr(
                config, "vad_threshold", self.DEFAULT_THRESHOLD
            )

            self.state = "IDLE"

            self.buffer = np.array([], dtype=np.float32)
            self.grace_start_time = 0
            self.boundary_peek_result = False

            # Smart chunking state
            self.long_utterance_mode = False
            self.long_utterance_buffer = np.array([], dtype=np.float32)
            self.second_thread_started = False

            # Constants
            self.SAMPLE_RATE = 16000
            self.MAX_AUDIO_SAMPLES = 40 * 16000  # 40s cap (Canary 1B limit)
            self.LONG_PAUSE_TIMEOUT_MS = 6000  # 6s for mid-sentence pauses

        def reset(self):
            self.state = "IDLE"
            self.buffer = np.array([], dtype=np.float32)
            self.grace_start_time = 0
            self.current_grace_timeout = 0
            self.boundary_peek_result = False
            self.long_utterance_mode = False
            self.long_utterance_buffer = np.array([], dtype=np.float32)
            self.second_thread_started = False

        def analyze_energy(self, chunk):
            """Return True if chunk has speech energy"""
            rms = np.sqrt(np.mean(chunk**2))
            return rms >= self.ENERGY_THRESHOLD

        def has_sentence_boundary(self, text: str) -> bool:
            """Check if text ends with a sentence boundary"""
            if not text:
                return False
            
            clean = text.strip()

            # EXPLICITLY IGNORE ELLIPSES
            # If it ends in '..' or '...', it is a pause, not a finish.
            if clean.endswith("..") or clean.endswith("..."):
                return False

            # Check for common sentence terminators
            terminators = [".", "?", "!", "。", "？", "！"]
            return any(clean.endswith(t) for t in terminators)

        def peek_buffer_boundary(self) -> bool:
            """
            Peek at the last 2 seconds of buffer to check for sentence boundary.
            Returns True if boundary detected.
            """
            if len(self.buffer) < 16000:  # Need at least 1s
                return False

            # Take last 2 seconds
            tail_samples = 32000
            peek_audio = (
                self.buffer[-tail_samples:]
                if len(self.buffer) > tail_samples
                else self.buffer
            )

            try:
                # Quick transcribe (no detailed logging)
                text = self.asr.transcribe(peek_audio, language=self.lang_hint)
                if self.has_sentence_boundary(text):
                    logger.info(
                        f"👀 Peek detected boundary in '{text}' - requesting GRACE period"
                    )
                    return True
            except Exception as e:
                logger.error(f"Peek failed: {e}")

            return False

        def process_chunk(self, chunk) -> Optional[np.ndarray]:
            """
            Process an audio chunk.
            Returns:
                None: Continue accumulating
                np.ndarray: Audio buffer to flush (utterance complete)
            """
            has_energy = self.analyze_energy(chunk)

            # Always handle long utterance accumulation first if active
            if self.long_utterance_mode and has_energy:
                self.long_utterance_buffer = np.concatenate(
                    [self.long_utterance_buffer, chunk]
                )

            if self.state == "IDLE":
                if has_energy:
                    # Transition to SPEECH
                    self.state = "SPEECH"
                    self.buffer = np.concatenate([self.buffer, chunk])
                else:
                    # Still IDLE, do nothing
                    pass

            elif self.state == "SPEECH":
                if has_energy:
                    self.buffer = np.concatenate([self.buffer, chunk])

                    # Check for Long Utterance conditions
                    current_samples = len(self.buffer)

                    # Enter long mode at 85%
                    if current_samples >= self.MAX_AUDIO_SAMPLES * 0.85:
                        if not self.long_utterance_mode:
                            logger.info(
                                f"📊 Entering long utterance mode ({current_samples / self.SAMPLE_RATE:.1f}s)"
                            )
                            self.long_utterance_mode = True
                            self.long_utterance_buffer = self.buffer.copy()

                        # Start second thread
                        if not self.second_thread_started:
                            logger.info("🔄 Starting second thread for overflow")
                            self.second_thread_started = True

                    # Force flush at 100%
                    if current_samples >= self.MAX_AUDIO_SAMPLES:
                        logger.warning("⚠️ Safety cap reached - forcing flush")
                        audio_to_flush = self.buffer.copy()
                        self.reset()
                        return audio_to_flush

                else:
                    # Energy dropped -> Transition to GRACE
                    self.state = "GRACE"
                    self.grace_start_time = time.time()

                    # Peek for boundary and store result
                    self.boundary_peek_result = self.peek_buffer_boundary()

                    # Set DYNAMIC timeout based on boundary
                    if self.boundary_peek_result:
                        self.current_grace_timeout = self.config.silence_timeout_ms
                        logger.info(
                            f"⏸️  Boundary detected - GRACE: {self.current_grace_timeout}ms"
                        )
                    else:
                        self.current_grace_timeout = self.LONG_PAUSE_TIMEOUT_MS
                        logger.info(
                            f"⏸️  Mid-sentence pause - LONG GRACE: {self.current_grace_timeout}ms"
                        )

            elif self.state == "GRACE":
                if has_energy:
                    # Resumed speaking
                    logger.info("🔄 Re-activated during grace period")
                    self.state = "SPEECH"
                    self.buffer = np.concatenate([self.buffer, chunk])
                    if self.long_utterance_mode:
                        self.long_utterance_buffer = np.concatenate(
                            [self.long_utterance_buffer, chunk]
                        )
                else:
                    # Still silent - check timeout
                    elapsed_ms = (time.time() - self.grace_start_time) * 1000
                    
                    if elapsed_ms >= self.current_grace_timeout:
                        # Grace expired
                        if self.boundary_peek_result:
                            logger.info("✅ Grace expired with boundary - FLUSHING")
                            audio_to_flush = self.buffer.copy()
                            self.reset()

                            # Filter short noise bursts
                            if len(audio_to_flush) < self.SAMPLE_RATE * 0.3:  # < 0.3s
                                logger.debug("Discarding short noise burst")
                                return None

                            return audio_to_flush
                        else:
                            # User paused for >5s mid-sentence.
                            # DO NOT FLUSH. Go to IDLE and preserve the buffer.
                            # This allows "unlimited" thinking time.
                            logger.info("⏳ Long pause (5s) - Waiting for more speech (Buffer Preserved)")
                            self.state = "IDLE"
                            # We do NOT call self.reset() here, so self.buffer is kept.
                            return None
            return None

    # Play start sound and log daemon start
    sound.play_start()
    telemetry.log_daemon_start()

    audio_queue = queue.Queue()
    # Process utterances in background thread so recording never blocks
    executor = ThreadPoolExecutor(max_workers=3)

    def audio_callback(indata, frames, time_info, status):
        audio_queue.put(indata[:, 0].copy())

    def process_utterance(
        audio_buffer: np.ndarray, silence_trigger_ms: int, is_forced_flush: bool = False
    ) -> None:
        """Process complete utterance: transcribe → LLM → output → log"""

        audio_duration = len(audio_buffer) / 16000

        # Check if this is likely an artifact based on duration and RMS
        buffer_rms = np.sqrt(np.mean(audio_buffer**2)) if len(audio_buffer) > 0 else 0
        if audio_duration < 0.5 and buffer_rms < 0.02:
            logger.debug(
                f"⏭️  Skipping likely artifact: {audio_duration:.1f}s, RMS={buffer_rms:.3f}"
            )
            return

        # Handle long utterances with smart chunking
        if audio_duration > 38.0:  # Close to 40s limit
            logger.info(
                f"📝 Long utterance detected ({audio_duration:.1f}s) - using smart chunking"
            )
            chunk_results = process_long_utterance(asr, audio_buffer, lang_hint)

            # Combine results
            all_text = " ".join([text for text, _ in chunk_results if text])
            total_inference_time = sum([inf_time for _, inf_time in chunk_results])

            logger.info(f"🔗 Combined {len(chunk_results)} chunks: {all_text[:100]}...")
            text = all_text
            inference_time_ms = total_inference_time
        else:
            # Normal single transcription
            text, inference_time_ms = transcribe_chunk(asr, audio_buffer, lang_hint)

        if not text:
            return

        # Check for artifacts
        if text_processor.is_artifact(text):
            logger.info(
                f"⏭️  Filtered artifact: '{text}' (duration: {audio_duration:.1f}s, silence: {silence_trigger_ms}ms)"
            )
            return
        # Process with profile awareness (handles preprocessing and wake words)
        result = text_processor.process_with_profile(text, audio_duration)
        
        # Calculate word count on the processed text
        word_count = len(result.text.split())

        # Log wake word detection
        if result.wake_word_detected:
            logger.info(f"🔔 Wake word detected, profile: {result.profile_id}")

        # Get profile-specific LLM prompt if needed
        profile = profile_manager.get_current_profile()

        llm_output = None
        llm_processed = False

        # LLM processing (skip for short utterances)
        if config.enable_llm and llm and word_count >= config.min_words_for_llm:
            logger.info(
                f"🧠 Processing via LLM ({word_count} words, profile: {profile.name}): {text[:50]}..."
            )

            # Use profile-specific prompt if available
            prompt = profile.llm_prompt
            if prompt:
                original_prompt = llm.prompt_template
                llm.prompt_template = prompt

            llm_output = llm.process_text(result.text)

            # Restore prompt if changed
            if prompt:
                llm.prompt_template = original_prompt

            llm_processed = True
            logger.info(f"✅ Result: {llm_output}")
        else:
            if config.enable_llm and word_count < config.min_words_for_llm:
                logger.info(
                    f"⏭️  Skipping LLM (only {word_count} words, min {config.min_words_for_llm})"
                )
            else:
                logger.info(
                    f"⌨️  Typing raw (profile: {profile.name}): {result.text[:50]}..."
                )
            llm_output = result.text

        # Final artifact check after LLM processing
        if text_processor.is_artifact(llm_output):
            logger.info(f"⏭️  Filtered artifact (post-LLM): '{llm_output}'")
            return
        logger.info(f"✅ Artifact check passed, proceeding to output")

        # Format output based on profile output format
        output_text = text_processor.format_for_output(
            llm_output.rstrip(), profile.output_format
        )

        # Output using WBind (original simple approach with profile support)
        logger.info(
            f"⌨️  TYPING: {output_text[:100]}{'...' if len(output_text) > 100 else ''}"
        )
        with output_lock:
            wbind.type_text(output_text)
            # Press configured output keys (usually space for default)
            for key in profile.output_keys:
                wbind.press_key(key)

        # Log telemetry
        telemetry.log_inference(
            text, inference_time_ms / 1000, audio_duration, success=True
        )

        # Log to JSON buffer
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "audio_duration_s": round(audio_duration, 2),
            "silence_trigger_ms": silence_trigger_ms,
            "transcription_raw": text_raw,
            "transcription_clean": text if text != text_raw else None,
            "inference_time_ms": inference_time_ms,
            "llm_output": llm_output,
            "llm_processed": llm_processed,
            "word_count": word_count,
            "profile_id": profile.name,
            "output_format": profile.output_format,
            "output_keys": profile.output_keys,
            "is_artifact": False,
            "processing_mode": "chunked" if audio_duration > 38.0 else "single",
        }
        json_logger.append(record)

    def process_audio():
        # Get threshold for logging
        threshold = getattr(
            config, "vad_threshold", RealisticEnergyStateMachine.DEFAULT_THRESHOLD
        )
        current_profile = profile_manager.get_current_profile()
        logger.info(
            f"🎤 Listening... (Profile: {current_profile.name}, Threshold: {threshold:.4f}, Grace: {config.silence_timeout_ms}ms)"
        )

        # Initialize State Machine
        sm = RealisticEnergyStateMachine(config, asr, lang_hint)

        # Initialize Wake Word if enabled
        oww_model = None
        if config.enable_wakeword:
            try:
                logger.info(
                    f"⏳ Loading wake word model: '{config.wakeword_phrase}'..."
                )
                import openwakeword

                logger.info(f"DEBUG: openwakeword path: {openwakeword.__file__}")
                from openwakeword.model import Model

                # Simplest initialization - loads all defaults including 'hey_jarvis'
                logger.info("DEBUG: Attempting Model() instantiation...")
                oww_model = Model()

                logger.info("🟢 Wake word system ready")
            except Exception as e:
                import traceback

                logger.error(f"❌ Failed to load wake word system: {e}")
                logger.error(traceback.format_exc())
                logger.error("  (Try: pip install openwakeword)")
                config.enable_wakeword = False

        # Audio loop
        sample_rate = 16000
        chunk_size = 1600  # 100ms

        # Application State
        waiting_for_wake_word = config.enable_wakeword
        last_activity_time = time.time()

        if waiting_for_wake_word:
            logger.info(f"💤 Waiting for wake word: '{config.wakeword_phrase}'")

        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            blocksize=chunk_size,
            callback=audio_callback,
        ):
            while not shutdown_requested:
                try:
                    chunk = audio_queue.get(timeout=1.0)

                    # --- Wake Word Logic ---
                    if waiting_for_wake_word:
                        if oww_model:
                            # Convert to int16 for OWW (safest for prediction)
                            chunk_int16 = (chunk * 32767).astype(np.int16)
                            prediction = oww_model.predict(chunk_int16)

                            score = prediction.get(config.wakeword_phrase, 0)
                            if score > 0.5:
                                logger.info(
                                    f"🔔 Wake word detected! (Score: {score:.2f})"
                                )
                                sound.play_start()
                                waiting_for_wake_word = False
                                last_activity_time = time.time()
                                sm.reset()
                                # Discard this chunk for VAD to avoid processing the wake word
                                continue
                        else:
                            # Fallback if model failed to load but flag still true (unlikely)
                            waiting_for_wake_word = False

                    # --- VAD Logic ---
                    else:
                        # Auto-sleep check
                        if config.enable_wakeword:
                            if sm.state == "IDLE":
                                elapsed = (time.time() - last_activity_time) * 1000
                                if elapsed > config.wakeword_timeout_ms:
                                    logger.info(
                                        f"💤 Auto-sleep after {config.wakeword_timeout_ms / 1000}s silence"
                                    )
                                    sound.play_end()
                                    waiting_for_wake_word = True
                                    if oww_model:
                                        oww_model.reset()
                                    continue
                            else:
                                # We are speaking or processing -> keep awake
                                last_activity_time = time.time()

                        # Process chunk via State Machine
                        audio_to_flush = sm.process_chunk(chunk)

                        if audio_to_flush is not None:
                            last_activity_time = time.time()  # Update activity on flush
                            # Dispatch
                            executor.submit(
                                process_utterance,
                                audio_to_flush,
                                int(config.silence_timeout_ms),
                            )

                except queue.Empty:
                    continue

    try:
        process_audio()
    finally:
        # Graceful shutdown
        logger.info("\n" + "=" * 80)
        logger.info("🧹 Cleaning up resources...")
        logger.info("=" * 80)

        # Wait for any pending transcriptions to finish
        executor.shutdown(wait=True)
        logger.info("✅ Processing queue flushed")

        # Log shutdown telemetry
        telemetry.log_daemon_stop()
        logger.info("✅ Telemetry logged")

        # Play end sound
        sound.play_end()
        logger.info("✅ End sound played")

        logger.info("=" * 80)
        logger.info("👋 Canary 1B daemon stopped gracefully")
        logger.info("=" * 80 + "\n")


def main():
    # Load profiles for help text
    try:
        from utils.config import ConfigManager
        from utils.profile_manager import ProfileManager
        pm = ProfileManager(ConfigManager())
        profile_help = "\nAvailable Profiles & Wake Words:\n" + pm.get_profile_summary()
    except Exception:
        profile_help = "\n(Could not load profiles for help text)"

    parser = get_base_parser("Sovd - Canary STT with Auto-Model Selection")
    add_common_listening_args(parser)
    add_profile_args(parser)
    add_transcribe_args(parser)
    parser.add_argument("--lang", default="auto", help="Language hint")
    
    # Add profile summary to epilog
    parser.epilog = profile_help
    
    args = parser.parse_args()

    # If --scribe is used, switch to single transcription mode
    if args.scribe:
        transcribe_file_cli(args)
        sys.exit(0)
        
    run(args)


def main_flash():
    """Entry point for covdf command - flash model by default, but supports --auto and --model"""
    # Load profiles for help text
    try:
        from utils.config import ConfigManager
        from utils.profile_manager import ProfileManager
        pm = ProfileManager(ConfigManager())
        profile_help = "\nAvailable Profiles & Wake Words:\n" + pm.get_profile_summary()
    except Exception:
        profile_help = "\n(Could not load profiles for help text)"

    parser = get_base_parser("Sovd Flash - Canary 180M Flash Daemon")
    add_common_listening_args(parser)
    add_profile_args(parser)
    add_transcribe_args(parser)
    parser.add_argument("--lang", default="auto", help="Language hint")
    
    # Add profile summary to epilog
    parser.epilog = profile_help
    
    args = parser.parse_args()

    # If --scribe is used, switch to single transcription mode
    if args.scribe:
        transcribe_file_cli(args)
        sys.exit(0)
        
    run(args)


if __name__ == "__main__":
    main()
