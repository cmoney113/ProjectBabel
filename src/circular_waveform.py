"""
Circular Waveform Widget for Voice Recording
Real-time animated circular waveform display with voice-responsive animations
"""

import math
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal, QPointF, QRectF
from PySide6.QtGui import QPainter, QBrush, QPen, QColor, QRadialGradient, QConicalGradient
from PySide6.QtWidgets import QWidget


class CircularWaveformWidget(QWidget):
    """Circular waveform display widget with real-time voice animation"""
    
    # Sensitivity levels
    SENSITIVITY_LEVELS = {
        'Low': 0.3,
        'Medium': 0.6, 
        'High': 1.0,
        'Custom': None
    }
    
    # States
    STATE_IDLE = 0
    STATE_RECORDING = 1
    STATE_PROCESSING = 2
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Widget properties
        self.setMinimumSize(120, 120)
        self.setMaximumSize(200, 200)
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Waveform data
        self.waveform_data = np.zeros(72)  # 72 segments (5° each)
        self.audio_history = []  # Rolling window of audio data
        self.max_history = 50  # Keep last 50 audio samples
        
        # Animation properties
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_frame = 0
        self.rotation_angle = 0
        
        # Sensitivity settings
        self.sensitivity = self.SENSITIVITY_LEVELS['Medium']
        self.custom_sensitivity = 0.6
        self.smoothing_factor = 0.8  # Smooth transitions
        
        # Visual properties
        self.base_radius = 40
        self.max_amplitude = 20
        self.glow_intensity = 0.5
        self.pulse_phase = 0
        
        # State management
        self.current_state = self.STATE_IDLE
        self.is_recording = False
        self.recording_start_time = None
        
        # Colors (will be updated with theme)
        self.bg_color = QColor("#1a1a2e")
        self.waveform_color = QColor("#4A90E2")
        self.glow_color = QColor("#6BB6FF")
        self.processing_color = QColor("#FF6B6B")
        
        # Start animation timer
        self.animation_timer.start(16)  # ~60fps
        
    def set_state(self, state):
        """Set the current state and update visual appearance"""
        if self.current_state != state:
            self.current_state = state
            self.update()
            
            # Update timer based on state
            if state == self.STATE_RECORDING:
                self.is_recording = True
                self.recording_start_time = time.time()
            else:
                self.is_recording = False
                if state == self.STATE_IDLE:
                    self.waveform_data.fill(0)
                    self.audio_history.clear()
    
    def add_audio_data(self, audio_chunk):
        """Add new audio data to the waveform"""
        if not self.is_recording:
            return
            
        # Calculate RMS energy from audio chunk
        if len(audio_chunk) > 0:
            rms = np.sqrt(np.mean(audio_chunk**2))
            
            # Apply sensitivity scaling
            scaled_rms = rms * self.get_effective_sensitivity()
            
            # Add to history with smoothing
            self.audio_history.append(scaled_rms)
            if len(self.audio_history) > self.max_history:
                self.audio_history.pop(0)
            
            # Update waveform data with smoothing
            self.update_waveform_from_history()
    
    def get_effective_sensitivity(self):
        """Get the effective sensitivity value"""
        if self.sensitivity is None:  # Custom mode
            return self.custom_sensitivity
        return self.sensitivity
    
    def set_sensitivity(self, level, custom_value=None):
        """Set sensitivity level"""
        if level in self.SENSITIVITY_LEVELS:
            self.sensitivity = self.SENSITIVITY_LEVELS[level]
            if level == 'Custom' and custom_value is not None:
                self.custom_sensitivity = max(0.1, min(2.0, custom_value))
    
    def update_waveform_from_history(self):
        """Update circular waveform data from audio history"""
        if not self.audio_history:
            return
            
        # Map audio history to circular segments
        history_len = len(self.audio_history)
        segments = len(self.waveform_data)
        
        # Smooth transition using weighted average
        for i in range(segments):
            # Calculate which part of history this segment represents
            history_index = int((i / segments) * history_len)
            if history_index < history_len:
                # Apply smoothing to avoid harsh jumps
                target_value = self.audio_history[history_index]
                current_value = self.waveform_data[i]
                self.waveform_data[i] = (current_value * self.smoothing_factor + 
                                       target_value * (1 - self.smoothing_factor))
    
    def update_animation(self):
        """Update animation frame"""
        self.animation_frame += 1
        
        if self.current_state == self.STATE_RECORDING:
            # Subtle rotation for recording state
            self.rotation_angle += 0.5
            # Gentle pulsing effect
            self.pulse_phase += 0.1
            
        elif self.current_state == self.STATE_PROCESSING:
            # Faster rotation for processing
            self.rotation_angle += 3.0
            
        self.update()
    
    def paintEvent(self, event):
        """Custom painting for the circular waveform"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get widget center and radius
        center = self.rect().center()
        size = min(self.width(), self.height())
        base_radius = size // 3
        
        # Draw background circle
        self.draw_background(painter, center, base_radius)
        
        # Draw waveform based on state
        if self.current_state == self.STATE_IDLE:
            self.draw_idle_state(painter, center, base_radius)
        elif self.current_state == self.STATE_RECORDING:
            self.draw_recording_state(painter, center, base_radius)
        elif self.current_state == self.STATE_PROCESSING:
            self.draw_processing_state(painter, center, base_radius)
    
    def draw_background(self, painter, center, base_radius):
        """Draw the background circle"""
        # Create gradient for background
        gradient = QRadialGradient(center, base_radius)
        gradient.setColorAt(0, QColor("#16213e"))
        gradient.setColorAt(1, QColor("#0f3460"))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor("#2c3e50"), 2))
        
        # Draw main circle
        painter.drawEllipse(center, base_radius, base_radius)
    
    def draw_idle_state(self, painter, center, base_radius):
        """Draw idle state with subtle animation"""
        # Subtle pulsing circle
        pulse_amplitude = 3 * (0.5 + 0.5 * math.sin(self.pulse_phase))
        
        painter.setBrush(QBrush(QColor("#4A90E2")))
        painter.setPen(QPen(QColor("#6BB6FF"), 2))
        
        # Draw pulsing inner circle
        painter.drawEllipse(center, base_radius // 3 + pulse_amplitude, 
                           base_radius // 3 + pulse_amplitude)
    
    def draw_recording_state(self, painter, center, base_radius):
        """Draw active recording with voice-responsive waveform"""
        # Save painter state
        painter.save()
        
        # Apply rotation
        painter.translate(center.x(), center.y())
        painter.rotate(self.rotation_angle)
        painter.translate(-center.x(), -center.y())
        
        # Draw waveform segments
        segments = len(self.waveform_data)
        angle_step = 360 / segments
        
        for i, amplitude in enumerate(self.waveform_data):
            if amplitude > 0.01:  # Only draw significant audio
                angle = math.radians(i * angle_step)
                
                # Calculate positions
                inner_radius = base_radius * 0.8
                outer_radius = inner_radius + amplitude * self.max_amplitude
                
                # Calculate points
                x1 = center.x() + inner_radius * math.cos(angle)
                y1 = center.y() + inner_radius * math.sin(angle)
                x2 = center.x() + outer_radius * math.cos(angle)
                y2 = center.y() + outer_radius * math.sin(angle)
                
                # Create gradient for this segment
                segment_gradient = QLinearGradient(x1, y1, x2, y2)
                segment_gradient.setColorAt(0, self.waveform_color)
                segment_gradient.setColorAt(1, self.glow_color)
                
                # Draw waveform segment
                painter.setPen(QPen(QBrush(segment_gradient), 3, Qt.RoundCap))
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        
        # Draw center glow
        glow_radius = base_radius // 4
        glow_intensity = 0.3 + 0.2 * math.sin(self.pulse_phase)
        
        glow_gradient = QRadialGradient(center, glow_radius)
        glow_gradient.setColorAt(0, QColor("#6BB6FF"))
        glow_gradient.setColorAt(1, QColor("#4A90E2"))
        
        painter.setBrush(QBrush(glow_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, glow_radius, glow_radius)
        
        painter.restore()
    
    def draw_processing_state(self, painter, center, base_radius):
        """Draw processing state with spinning animation"""
        # Draw spinning segments
        segments = 12
        angle_step = 360 / segments
        
        for i in range(segments):
            angle = math.radians(i * angle_step + self.rotation_angle)
            
            # Calculate opacity based on position
            opacity = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(
                math.radians(i * angle_step * 2 + self.rotation_angle * 3)))
            
            color = QColor(self.processing_color)
            color.setAlphaF(opacity)
            
            # Calculate segment position
            segment_length = base_radius // 3
            inner_radius = base_radius * 0.7
            outer_radius = inner_radius + segment_length
            
            x1 = center.x() + inner_radius * math.cos(angle)
            y1 = center.y() + inner_radius * math.sin(angle)
            x2 = center.x() + outer_radius * math.cos(angle)
            y2 = center.y() + outer_radius * math.sin(angle)
            
            # Draw segment
            painter.setPen(QPen(color, 4, Qt.RoundCap))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    
    def sizeHint(self):
        """Recommended size for the widget"""
        from PySide6.QtCore import QSize
        return QSize(120, 120)
    
    def get_recording_duration(self):
        """Get current recording duration in seconds"""
        import time
        if self.is_recording and self.recording_start_time:
            return time.time() - self.recording_start_time
        return 0