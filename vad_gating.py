"""
VAD (Voice Activity Detection) Gating System for Vokoro - REFACTORED

ARCHITECTURAL CHANGE: Event-driven architecture replacing polling.
Previously used a monitoring thread that polled every 50-100ms.
Now triggers flush callbacks immediately when silence threshold is reached.

RATIONALE:
- Polling wastes CPU cycles checking when nothing changed
- Event-driven responds immediately at threshold crossing
- More precise timing (exactly at threshold, not rounded to polling interval)
- Cleaner architecture without background threads
"""

import logging
import time
import threading
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class VADConfig:
    """Configuration for VAD gating"""
    silence_timeout_ms: int = 350  # Time before flushing accumulated text
    min_accumulated_text_length: int = 1  # Minimum chars before considering flush
    noise_threshold: float = 0.05  # Audio level threshold for silence detection
    vad_enabled: bool = True
    debug_mode: bool = False


@dataclass
class VADSegment:
    """Represents a single VAD segment"""
    text: str
    start_time: float
    end_time: float
    confidence: Optional[float] = None
    is_final: bool = False
    silence_duration_ms: int = 0


class VADGatingEngine:
    """
    Main VAD gating engine with text accumulation and buffer management.
    
    ARCHITECTURE: Event-driven with timeout timer
    - No background monitoring thread (polling removed)
    - Uses single-shot timer to detect silence after segment ends
    - Timer fires if no new segment arrives within silence_timeout_ms
    - More precise timing, lower CPU usage
    """
    
    def __init__(self, config: VADConfig, flush_callback: Optional[Callable] = None):
        """
        Initialize VAD gating engine.
        
        Args:
            config: VAD configuration
            flush_callback: Callback when buffer is flushed (receives accumulated text)
        """
        self.config = config
        self.flush_callback = flush_callback
        
        # Text accumulation
        self.accumulated_text = ""
        self.segment_queue: deque = deque()
        self.accumulated_segments = []
        self.accumulation_start_time = None
        
        # Silence detection
        self.last_segment_time = time.time()
        self._timeout_timer = None
        self._timer_lock = threading.Lock()
        
        # Threading safety
        self.lock = threading.RLock()
        
        # Statistics
        self.total_segments_accumulated = 0
        self.total_flushes = 0
        self.total_text_accumulated = 0
        self.last_flush_time = time.time()
        
        logger.info(f"VAD Gating Engine initialized with config: {config}")
        logger.info("ARCHITECTURE: Event-driven with timeout timer (no polling)")
    
    def _start_timeout_timer(self):
        """Start or restart the silence timeout timer."""
        with self._timer_lock:
            # Cancel existing timer
            if self._timeout_timer is not None:
                self._timeout_timer.cancel()
            
            # Create new single-shot timer
            self._timeout_timer = threading.Timer(
                interval=self.config.silence_timeout_ms / 1000.0,
                function=self._on_silence_timeout
            )
            self._timeout_timer.daemon = True
            self._timeout_timer.start()
    
    def _on_silence_timeout(self):
        """
        Called when silence timeout fires.
        Checks if silence has elapsed since last segment and flushes if needed.
        """
        with self.lock:
            # Check if we have accumulated text
            if not self.accumulated_text.strip():
                return
            
            # Calculate silence duration since last segment
            current_time = time.time()
            silence_duration_ms = (current_time - self.last_segment_time) * 1000
            
            # Only flush if silence threshold has been exceeded
            if silence_duration_ms >= self.config.silence_timeout_ms:
                logger.info(
                    f"VAD: Silence timeout ({silence_duration_ms:.0f}ms >= "
                    f"{self.config.silence_timeout_ms}ms) - "
                    f"Flushing {len(self.accumulated_text)} chars"
                )
                self.flush_buffer()
    
    def add_segment(
        self,
        text: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        confidence: Optional[float] = None,
        is_final: bool = False,
    ) -> None:
        """
        Add a transcription segment to accumulation buffer.
        
        Args:
            text: Transcribed text
            start_time: Audio segment start time
            end_time: Audio segment end time
            confidence: ASR confidence score
            is_final: Whether this is final transcription
        """
        if not text.strip():
            return
        
        with self.lock:
            if self.accumulation_start_time is None:
                self.accumulation_start_time = time.time()
            
            self.last_segment_time = time.time()
            
            segment = VADSegment(
                text=text,
                start_time=start_time or time.time(),
                end_time=end_time or time.time(),
                confidence=confidence,
                is_final=is_final,
            )
            
            self.accumulated_segments.append(segment)
            self.segment_queue.append(segment)
            
            # Build accumulated text
            if self.accumulated_text:
                self.accumulated_text += " " + text
            else:
                self.accumulated_text = text
            
            self.total_segments_accumulated += 1
            self.total_text_accumulated += len(text)
            
            # Start silence timeout timer - fires if no new segment arrives
            self._start_timeout_timer()
            
            if self.config.debug_mode:
                logger.debug(
                    f"VAD: Added segment ({len(text)} chars) | "
                    f"Total accumulated: {len(self.accumulated_text)} chars"
                )
    
    def detect_silence(self) -> bool:
        """
        Check if silence threshold has been reached since last segment.
        
        Returns:
            bool: True if accumulated text should be flushed
        """
        with self.lock:
            if not self.accumulated_text.strip():
                return False
            
            current_time = time.time()
            silence_duration_ms = (current_time - self.last_segment_time) * 1000
            
            if silence_duration_ms >= self.config.silence_timeout_ms:
                self.flush_buffer()
                return True
            
            return False
    
    def flush_buffer(self) -> Optional[str]:
        """
        Flush accumulated text buffer and trigger processing.
        
        Returns:
            str: Accumulated text that was flushed, or None if nothing to flush
        """
        with self.lock:
            if not self.accumulated_text.strip():
                return None
            
            text_to_flush = self.accumulated_text.strip()
            
            # Add trailing space for proper separation between flushes
            text_to_flush_with_space = text_to_flush + " "
            
            if self.config.debug_mode:
                logger.debug(
                    f"VAD: Flushing buffer ({len(text_to_flush)} chars, "
                    f"{len(self.accumulated_segments)} segments)"
                )
            
            # Call flush callback if registered
            if self.flush_callback:
                try:
                    self.flush_callback({
                        'text': text_to_flush_with_space,
                        'segments': self.accumulated_segments.copy(),
                        'segment_count': len(self.accumulated_segments),
                        'accumulated_chars': len(text_to_flush_with_space),
                        'flush_time': time.time(),
                    })
                except Exception as e:
                    logger.error(f"VAD: Error in flush callback: {e}")
            
            # Reset accumulation
            self.accumulated_text = ""
            self.accumulated_segments.clear()
            self.segment_queue.clear()
            self.accumulation_start_time = None
            
            # Cancel any pending timeout timer
            with self._timer_lock:
                if self._timeout_timer is not None:
                    self._timeout_timer.cancel()
                    self._timeout_timer = None
            
            self.total_flushes += 1
            self.last_flush_time = time.time()
            
            return text_to_flush_with_space
    
    # REMOVED: start_monitor() - No longer needed with event-driven architecture
    # REMOVED: stop_monitor() - No longer needed with event-driven architecture
    # REMOVED: _monitor_silence() - No longer needed with event-driven architecture
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get VAD gating statistics.
        
        Returns:
            Dictionary with current statistics
        """
        with self.lock:
            accumulation_duration = 0
            if self.accumulation_start_time:
                accumulation_duration = time.time() - self.accumulation_start_time
            
            current_time = time.time()
            silence_duration_ms = (current_time - self.last_segment_time) * 1000
            
            return {
                'total_segments_accumulated': self.total_segments_accumulated,
                'total_flushes': self.total_flushes,
                'total_text_accumulated': self.total_text_accumulated,
                'current_accumulated_text_length': len(self.accumulated_text),
                'current_segment_count': len(self.accumulated_segments),
                'accumulation_duration_seconds': accumulation_duration,
                'silence_duration_ms': silence_duration_ms,
                'is_accumulated': bool(self.accumulated_text.strip()),
                'last_flush_time': self.last_flush_time,
                'silence_timeout_ms': self.config.silence_timeout_ms,
                'architecture': 'event-driven-with-timer',  # Mark architecture type
            }
    
    def reset(self) -> None:
        """Reset VAD gating engine to initial state"""
        with self.lock:
            self.accumulated_text = ""
            self.accumulated_segments.clear()
            self.segment_queue.clear()
            self.accumulation_start_time = None
            self.last_segment_time = time.time()
            
            # Cancel any pending timeout timer
            with self._timer_lock:
                if self._timeout_timer is not None:
                    self._timeout_timer.cancel()
                    self._timeout_timer = None
            
            self.total_segments_accumulated = 0
            self.total_flushes = 0
            self.total_text_accumulated = 0
            logger.info("VAD gating engine reset")
    
    def get_accumulated_text(self) -> str:
        """Get current accumulated text without flushing"""
        with self.lock:
            return self.accumulated_text if self.accumulated_text else ""
    
    def get_accumulated_segments(self) -> list:
        """Get current accumulated segments without flushing"""
        with self.lock:
            return self.accumulated_segments.copy()
