import math
import time
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QPalette, QRadialGradient, QLinearGradient, QFont 
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF, QRectF 


class Turntable(QWidget):
    """
    Custom QWidget representing a professional DJ turntable with vinyl-style scratch control.
    Features:
    - Real-time audio scrubbing with velocity tracking
    - Vinyl stop/start effects
    - Professional touch sensitivity
    - Pitch bending and control
    """
    # Signal emitted when the user scrubs (drags) the turntable
    # Passes the new position as a fraction (0.0 to 1.0)
    positionScrubbed = pyqtSignal(float)
    # Signal for pitch/speed control from outer ring
    pitchChanged = pyqtSignal(float)  # -8 to +8 range for typical DJ pitch
    # New signal for scratch speed (velocity-based scratching)
    scratchSpeed = pyqtSignal(float)  # Speed multiplier for real-time scrubbing
    # Signal for vinyl stop/start effect
    vinylStopStart = pyqtSignal(bool)  # True=stop, False=start

    def __init__(self, parent=None):
        """
        Initialize the Turntable widget with professional vinyl controls.

        Args:
            parent (QWidget, optional): Parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.angle = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.setInterval(20)  # 50 FPS

        # Add debounce timer for seeking
        self.seek_timer = QTimer(self)
        self.seek_timer.setSingleShot(True)
        self.seek_timer.timeout.connect(self._emit_seek_position)
        self.pending_seek_position = None

        self.is_dragging = False
        self.is_outer_ring = False  # Track if user is dragging outer ring
        self._is_playing = False
        self._was_playing = False
        self.last_mouse_pos = QPointF()
        self.base_rotation_speed = 2.5
        self.rotation_speed = self.base_rotation_speed
        self.current_pitch = 0.0  # Current pitch adjustment (-8 to +8)
        self.last_y = None  # For vertical pitch control
        
        # Professional vinyl scratch mode
        self.vinyl_mode = True  # Enable vinyl-style control by default
        self.scratch_velocity = 0.0  # Current scratch speed
        self.last_scratch_time = 0.0
        self.last_angle = 0.0
        self.scratch_history = []  # Store recent velocities for smoothing
        self.max_scratch_history = 5
        
        # Vinyl motor simulation
        self.motor_speed = 1.0  # Target speed (1.0 = normal)
        self.current_motor_speed = 1.0  # Actual speed (with inertia)
        self.motor_acceleration = 0.15  # How fast motor responds
        self.motor_deceleration = 0.3  # How fast motor slows down
        
        # Scratch sensitivity
        self.scratch_sensitivity = 1.5  # Multiplier for scratch speed

        # Animation properties
        self._hover_opacity = 0.0
        self._glow_phase = 0.0
        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._update_glow)
        self._glow_timer.start(50)  # 20 FPS

        # Styling - OPTIMIZED SIZE for side-by-side layout
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(150, 150)  # Large but fits with loop controls
        self.setMaximumSize(150, 150)  # Fixed size for consistent layout
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.transparent)
        self.setPalette(palette)

        # Enhanced color definitions
        self.colors = {
            'base': QColor(17, 17, 17, 200),
            'primary': QColor("#f3cf2c"),
            'glow': QColor("#f3cf2c"),
            'outer_ring': QColor("#f3cf2c").darker(120)
        }

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

    def _update_glow(self):
        """
        Update the glow phase for animation and trigger repaint if needed.
        """
        self._glow_phase = (self._glow_phase + 0.15) % (2 * math.pi)  # Faster animation
        # Always update to show continuous glow animation
        self.update()

    def enterEvent(self, event):
        """
        Handle mouse enter event to update hover opacity.

        Args:
            event: The QEnterEvent instance.
        """
        self._hover_opacity = 0.3
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """
        Handle mouse leave event to reset hover opacity.

        Args:
            event: The QLeaveEvent instance.
        """
        self._hover_opacity = 0.0
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        """
        Paint the turntable, including rings, grooves, hub, and indicators.

        Args:
            event: The QPaintEvent instance.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        center = QPointF(width / 2.0, height / 2.0)
        radius = min(width, height) / 2.0 - 10.0

        if radius <= 0:
            return

        # Draw outer ring (pitch control area)
        outer_ring_width = radius * 0.2
        outer_radius = radius
        inner_radius = radius - outer_ring_width
        
        # Draw outer ring with gradient
        outer_gradient = QRadialGradient(center, outer_radius)
        outer_gradient.setColorAt(0.8, self.colors['outer_ring'])  # Start of outer ring
        outer_gradient.setColorAt(1, self.colors['primary'])  # Edge of outer ring
        
        painter.setBrush(QBrush(outer_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, outer_radius, outer_radius)
        
        # Draw inner circle (scratch area)
        base_gradient = QRadialGradient(center, inner_radius)
        base_gradient.setColorAt(0, self.colors['base'])
        base_gradient.setColorAt(0.7, QColor(30, 30, 30, 200))
        base_gradient.setColorAt(1, QColor(40, 40, 40, 200))
        
        painter.setBrush(QBrush(base_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, inner_radius, inner_radius)

        # Draw concentric rings with enhanced glow effect
        num_rings = 3
        ring_spacing = inner_radius / (num_rings + 1)
        for i in range(num_rings):
            ring_radius = ring_spacing * (i + 1)
            glow_intensity = abs(math.sin(self._glow_phase + i * math.pi / num_rings))
            ring_color = QColor(self.colors['primary'])
            # Enhanced alpha range for more visible animation
            ring_color.setAlpha(int(80 + glow_intensity * 120))
            
            pen = QPen(ring_color, 2)  # Thicker lines
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, ring_radius, ring_radius)

        # Draw grooves
        num_grooves = 20
        groove_spacing = inner_radius / num_grooves
        for i in range(num_grooves):
            groove_radius = groove_spacing * (i + 1)
            groove_color = QColor(self.colors['primary'])
            groove_color.setAlpha(20)
            pen = QPen(groove_color, 0.5)
            painter.setPen(pen)
            painter.drawEllipse(center, groove_radius, groove_radius)

        # Draw center hub with metallic effect
        hub_radius = radius * 0.15
        hub_gradient = QRadialGradient(center, hub_radius)
        hub_gradient.setColorAt(0, QColor("#ffffff"))
        hub_gradient.setColorAt(0.5, self.colors['primary'])
        hub_gradient.setColorAt(1, QColor("#a08a1f"))
        
        painter.setBrush(QBrush(hub_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, hub_radius, hub_radius)

        # Draw position indicator with glow
        painter.save()
        painter.translate(center)
        painter.rotate(self.angle)

        # Draw glowing line with enhanced animation
        line_gradient = QLinearGradient(0, -hub_radius, 0, -radius)
        glow_intensity = abs(math.sin(self._glow_phase))
        primary_color = self.colors['primary']
        glow_color = QColor(primary_color)
        # Enhanced alpha range for more visible pulsing
        glow_color.setAlpha(int(180 + glow_intensity * 75))
        
        line_gradient.setColorAt(0, glow_color)
        line_gradient.setColorAt(1, QColor(primary_color.red(), 
                                         primary_color.green(),
                                         primary_color.blue(), 
                                         120))
        
        # Draw main line with thicker stroke for larger turntable
        painter.setPen(QPen(QBrush(line_gradient), 4))  # Thicker for visibility
        painter.drawLine(QPointF(0, -hub_radius), QPointF(0, -radius))

        # Add enhanced glow effect (always visible)
        glow_pen = QPen(self.colors['glow'], 7)  # Stronger glow for larger size
        glow_pen.setColor(QColor(primary_color.red(),
                               primary_color.green(),
                               primary_color.blue(),
                               int(60 + glow_intensity * 80)))
        painter.setPen(glow_pen)
        painter.drawLine(QPointF(0, -hub_radius), QPointF(0, -radius))

        painter.restore()

        # Draw pitch indicator if pitch is not 0
        if self.current_pitch != 0:
            pitch_text = f"{self.current_pitch:+.1f}%"
            painter.setPen(QPen(self.colors['primary']))
            painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))  # Adjusted font for medium turntable
            painter.drawText(QRectF(0, height - 18, width, 18), 
                           Qt.AlignmentFlag.AlignCenter, pitch_text)

        # Add hover effect
        if self._hover_opacity > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            hover_color = QColor(self.colors['primary'])
            hover_color.setAlpha(int(self._hover_opacity * 50))
            painter.setBrush(QBrush(hover_color))
            painter.drawEllipse(center, radius, radius)

    def set_playing(self, playing):
        """
        Controls visual rotation based on player state.

        Args:
            playing (bool): Whether the turntable should be rotating (playing state).
        """
        self._is_playing = playing
        if playing and not self.timer.isActive() and not self.is_dragging:
            self.timer.start()
        elif not playing and self.timer.isActive():
            self.timer.stop()

    def mousePressEvent(self, event):
        """
        Handle mouse press events for vinyl scratching or pitch control.
        Simulates vinyl stop effect when touched.

        Args:
            event: The QMouseEvent instance.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            center = QPointF(self.width() / 2, self.height() / 2)
            radius = min(self.width(), self.height()) / 2.0 - 10.0
            dist_from_center = QPointF(event.position() - center).manhattanLength()
            
            # Check if click is in outer ring (last 20% of radius)
            outer_ring_start = radius * 0.8
            self.is_outer_ring = dist_from_center >= outer_ring_start
            
            self.is_dragging = True
            self._was_playing = self._is_playing
            
            # For outer ring pitch control
            if self.is_outer_ring:
                self.last_y = event.position().y()
            else:
                # Inner area for vinyl scratching
                if self.vinyl_mode:
                    # Emit vinyl stop signal to slow down playback
                    self.vinylStopStart.emit(True)
                    self.motor_speed = 0.0  # Target stop
                    
                    # Initialize scratch tracking
                    self.last_scratch_time = time.time()
                    self.last_angle = self.angle
                    self.scratch_velocity = 0.0
                    self.scratch_history.clear()
                
                if self.timer.isActive():
                    self.timer.stop()
                self.last_mouse_pos = event.position()
            
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Handle mouse move events for vinyl-style scratching or pitch adjustment.
        Tracks velocity for real-time audio scrubbing.

        Args:
            event: The QMouseEvent instance.
        """
        if self.is_dragging:
            if self.is_outer_ring:
                # Outer ring: Vertical movement controls pitch
                if self.last_y is not None:
                    y_diff = event.position().y() - self.last_y
                    # Convert vertical movement to pitch change
                    # Scale factor determines sensitivity
                    pitch_change = -y_diff * 0.1  # Negative because up should increase pitch
                    new_pitch = max(-8.0, min(8.0, self.current_pitch + pitch_change))
                    if new_pitch != self.current_pitch:
                        self.current_pitch = new_pitch
                        # Update rotation speed based on pitch
                        self.rotation_speed = self.base_rotation_speed * (1.0 + (self.current_pitch / 100.0))
                        self.pitchChanged.emit(self.current_pitch)
                    self.last_y = event.position().y()
            else:
                # Inner area: Vinyl-style scratching
                current_pos = event.position()
                center = QPointF(self.width() / 2, self.height() / 2)
                
                prev_angle = math.atan2(self.last_mouse_pos.y() - center.y(), 
                                      self.last_mouse_pos.x() - center.x())
                current_angle = math.atan2(current_pos.y() - center.y(),
                                         current_pos.x() - center.x())
                
                angle_change = math.degrees(current_angle - prev_angle)
                if angle_change > 180:
                    angle_change -= 360
                elif angle_change < -180:
                    angle_change += 360
                    
                self.last_mouse_pos = current_pos
                
                new_angle = (self.angle + angle_change) % 360.0
                self.angle = new_angle

                # Calculate scratch velocity for vinyl mode
                if self.vinyl_mode:
                    current_time = time.time()
                    time_delta = current_time - self.last_scratch_time
                    
                    if time_delta > 0.001:  # Avoid division by zero
                        # Calculate angular velocity (degrees per second)
                        angular_velocity = angle_change / time_delta
                        
                        # Convert to playback speed multiplier
                        # Normal vinyl rotation is about 33.3 RPM = 200 degrees/sec
                        # This gives us a natural feel
                        base_vinyl_speed = 200.0  # degrees per second for 1x speed
                        scratch_speed = (angular_velocity / base_vinyl_speed) * self.scratch_sensitivity
                        
                        # Clamp to reasonable range (-10x to +10x for dramatic scratching)
                        scratch_speed = max(-10.0, min(10.0, scratch_speed))
                        
                        # Add to history for smoothing
                        self.scratch_history.append(scratch_speed)
                        if len(self.scratch_history) > self.max_scratch_history:
                            self.scratch_history.pop(0)
                        
                        # Calculate smoothed velocity
                        if self.scratch_history:
                            self.scratch_velocity = sum(self.scratch_history) / len(self.scratch_history)
                        else:
                            self.scratch_velocity = scratch_speed
                        
                        # Emit scratch speed for real-time audio control
                        self.scratchSpeed.emit(self.scratch_velocity)
                        
                        self.last_scratch_time = current_time
                        self.last_angle = self.angle

                # Emit seek position for precise positioning
                self.pending_seek_position = self.angle / 360.0
                if not self.seek_timer.isActive():
                    self.seek_timer.start(16)  # ~60fps for smoother scratching
            
            self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Handle mouse release events to end dragging and restore state.
        Simulates vinyl start effect when released.

        Args:
            event: The QMouseEvent instance.
        """
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            self.is_outer_ring = False
            self.last_y = None
            
            # Vinyl mode: Emit vinyl start signal with smooth ramp-up
            if self.vinyl_mode and not self.is_outer_ring:
                self.vinylStopStart.emit(False)  # Signal to start playback
                self.motor_speed = 1.0  # Target normal speed
                self.scratch_velocity = 0.0
                self.scratch_history.clear()
            
            # Restore playing state if it was playing before drag
            if self._was_playing:
                self._is_playing = True
                if not self.timer.isActive():
                    self.timer.start()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def rotate(self):
        """
        Rotate the turntable with smoother animation if playing and not dragging.
        """
        if self._is_playing and not self.is_dragging:
            self.angle = (self.angle + self.rotation_speed) % 360.0
            self.update()

    def _emit_seek_position(self):
        """
        Emit the pending seek position after debounce.
        """
        if self.pending_seek_position is not None:
            self.positionScrubbed.emit(self.pending_seek_position)
            self.pending_seek_position = None
    
    def set_vinyl_mode(self, enabled):
        """
        Enable or disable vinyl scratch mode.
        
        Args:
            enabled (bool): True to enable vinyl mode, False for standard mode.
        """
        self.vinyl_mode = enabled
        if not enabled:
            self.scratch_velocity = 0.0
            self.scratch_history.clear()
    
    def set_scratch_sensitivity(self, sensitivity):
        """
        Adjust the scratch sensitivity (how responsive scratching is).
        
        Args:
            sensitivity (float): Sensitivity multiplier (0.5 to 3.0 recommended).
        """
        self.scratch_sensitivity = max(0.1, min(5.0, sensitivity)) 