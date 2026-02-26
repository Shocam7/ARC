"""
AgentTile — Video-call style tile for an Artificial Friend (AF).
Shows a procedurally-generated avatar, name, status, and a speaking animation.
"""

import hashlib
import math

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QLinearGradient, QFont, QPixmap


def _name_to_hue(name: str) -> float:
    """Deterministically map an agent name to a hue (0–360)."""
    digest = int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)
    return (digest % 360)


class AvatarWidget(QWidget):
    """Procedurally generated geometric avatar based on the agent's name."""

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.hue = _name_to_hue(name)
        self.initials = "".join(w[0].upper() for w in name.split()[:2]) or name[:2].upper()
        self.setFixedSize(80, 80)

        # Pulse animation state
        self._pulse = 0.0
        self._speaking = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._tick_pulse)
        self._pulse_timer.start(30)
        self._pulse_phase = 0.0

    def set_speaking(self, speaking: bool):
        self._speaking = speaking
        self.update()

    def _tick_pulse(self):
        if self._speaking:
            self._pulse_phase += 0.12
            self._pulse = 0.5 + 0.5 * math.sin(self._pulse_phase)
        else:
            self._pulse_phase = 0.0
            self._pulse = 0.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        # ── Background circle ──────────────────────────────
        bg_color = QColor.fromHsvF(self.hue / 360.0, 0.6, 0.15)
        p.setBrush(QBrush(bg_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(4, 4, w - 8, h - 8)

        # ── Geometric rings (background decoration) ────────
        ring_color = QColor.fromHsvF(self.hue / 360.0, 0.7, 0.4, 0.3)
        pen = QPen(ring_color, 1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for i, r in enumerate([22, 30, 38]):
            alpha = int(120 - i * 30)
            ring_color.setAlpha(alpha)
            p.setPen(QPen(ring_color, 0.8))
            p.drawEllipse(int(cx - r), int(cy - r), r * 2, r * 2)

        # ── Speaking pulse ring ────────────────────────────
        if self._speaking and self._pulse > 0:
            pulse_color = QColor(0, 200, 255, int(180 * self._pulse))
            p.setPen(QPen(pulse_color, 2.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            r = int(38 + 4 * self._pulse)
            p.drawEllipse(int(cx - r), int(cy - r), r * 2, r * 2)

        # ── Initials ───────────────────────────────────────
        text_color = QColor.fromHsvF(self.hue / 360.0, 0.2, 0.95)
        p.setPen(text_color)
        font = QFont("Consolas", 18, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(QRect(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, self.initials)

        p.end()


class SpeakingBar(QWidget):
    """Animated equalizer bars shown when agent is speaking."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 14)
        self._bars = [0.3, 0.6, 1.0, 0.7, 0.4]
        self._phases = [i * 0.8 for i in range(5)]
        self._active = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)

    def set_active(self, active: bool):
        self._active = active
        self.update()

    def _tick(self):
        if self._active:
            for i in range(5):
                self._phases[i] += 0.25 + i * 0.07
                self._bars[i] = 0.35 + 0.65 * abs(math.sin(self._phases[i]))
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bar_w = 3
        gap = 2
        total = len(self._bars) * (bar_w + gap) - gap
        x0 = (w - total) // 2
        for i, v in enumerate(self._bars):
            bh = int(v * h) if self._active else 3
            x = x0 + i * (bar_w + gap)
            y = h - bh
            color = QColor(0, 200, 255, 200) if self._active else QColor(74, 90, 110, 120)
            p.fillRect(x, y, bar_w, bh, color)
        p.end()


class AgentTile(QWidget):
    """A single AF tile displayed in the ARC meeting grid."""

    clicked = pyqtSignal(str)  # emits agent name

    def __init__(self, agent_name: str, persona: str = "", parent=None):
        super().__init__(parent)
        self.agent_name = agent_name
        self.persona = persona
        self.setObjectName("agent_tile")
        self.setMinimumSize(220, 190)
        self._speaking = False
        self._glow_alpha = 0
        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._tick_glow)
        self._glow_timer.start(30)
        self._glow_phase = 0.0
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Avatar area ────────────────────────────────────
        avatar_container = QWidget()
        avatar_container.setObjectName("agent_tile")
        avatar_layout = QVBoxLayout(avatar_container)
        avatar_layout.setContentsMargins(0, 24, 0, 12)
        avatar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.avatar = AvatarWidget(self.agent_name)
        avatar_layout.addWidget(self.avatar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(avatar_container, 1)

        # ── Bottom bar ─────────────────────────────────────
        bar = QWidget()
        bar.setStyleSheet("background-color: rgba(7, 9, 15, 0.8); border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(12, 8, 12, 8)
        bar_layout.setSpacing(6)

        # Name
        self.name_label = QLabel(self.agent_name.upper())
        self.name_label.setObjectName("tile_name")

        # Speaking bars
        self.speaking_bar = SpeakingBar()

        # Status
        self.status_label = QLabel("IDLE")
        self.status_label.setObjectName("tile_status")
        self.status_label.setProperty("state", "idle")

        bar_layout.addWidget(self.name_label)
        bar_layout.addWidget(self.speaking_bar)
        bar_layout.addStretch()
        bar_layout.addWidget(self.status_label)

        layout.addWidget(bar)

    def set_speaking(self, speaking: bool):
        self._speaking = speaking
        self.avatar.set_speaking(speaking)
        self.speaking_bar.set_active(speaking)
        if speaking:
            self.set_status("SPEAKING", "speaking")
        else:
            self.set_status("IDLE", "idle")
        self.update()

    def set_status(self, text: str, state: str = "idle"):
        self.status_label.setText(text)
        self.status_label.setProperty("state", state)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def set_thinking(self):
        self.set_status("THINKING", "thinking")
        self.avatar.set_speaking(False)
        self.speaking_bar.set_active(False)

    def set_acting(self):
        self.set_status("ACTING", "acting")

    def _tick_glow(self):
        if self._speaking:
            self._glow_phase += 0.1
            self._glow_alpha = int(80 + 60 * math.sin(self._glow_phase))
        else:
            self._glow_alpha = 0
            self._glow_phase = 0.0
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._glow_alpha > 0:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            # Outer glow border
            glow_color = QColor(0, 200, 255, self._glow_alpha)
            pen = QPen(glow_color, 2)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(1, 1, self.width() - 2, self.height() - 2, 12, 12)
            p.end()

    def mousePressEvent(self, event):
        self.clicked.emit(self.agent_name)
        super().mousePressEvent(event)
