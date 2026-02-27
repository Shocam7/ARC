"""
AgentTile — Google Meet–style tile for an Artificial Friend (AF).

Visual hierarchy:
  • Dark tile (#3c4043) fills its grid cell
  • Animated Gemini 4-star in the center — illuminates when active
  • Name badge bottom-left (Meet-style)
  • Status chip bottom-right
  • Blue glow border when speaking (like Meet's active-speaker ring)
"""

import math
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QConicalGradient,
    QPainterPath, QFont, QLinearGradient, QRadialGradient
)

from arc.ui.landing_page import GeminiStarWidget   # reuse the shared star drawer


class AgentTile(QWidget):
    """A single AF video-call tile."""

    clicked = pyqtSignal(str)   # agent name

    def __init__(self, agent_name: str, persona: str = "", parent=None):
        super().__init__(parent)
        self.agent_name = agent_name
        self.persona    = persona
        self.setObjectName("meet_tile")
        self.setProperty("speaking", "false")
        self.setMinimumSize(160, 120)

        self._speaking  = False
        self._glow      = 0.0
        self._glow_dir  = 1

        # Glow border animation
        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._tick_glow)
        self._glow_timer.start(30)

        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Star area (fills tile) ──────────────────────────────────────────
        self._star_area = QWidget()
        self._star_area.setStyleSheet("background-color: transparent;")
        root.addWidget(self._star_area, 1)

        # ── Bottom badge bar ────────────────────────────────────────────────
        bar = QWidget()
        bar.setFixedHeight(36)
        bar.setStyleSheet("background-color: transparent;")
        bar_l = QHBoxLayout(bar)
        bar_l.setContentsMargins(10, 0, 10, 6)
        bar_l.setSpacing(4)

        self._name_badge = QLabel(self.agent_name)
        self._name_badge.setObjectName("tile_name_badge")

        self._status_lbl = QLabel("IDLE")
        self._status_lbl.setStyleSheet(
            "color:#9aa0a6;font-size:10px;font-weight:600;"
            "background:rgba(0,0,0,0.55);border-radius:3px;padding:2px 6px;"
        )

        bar_l.addWidget(self._name_badge)
        bar_l.addStretch()
        bar_l.addWidget(self._status_lbl)
        root.addWidget(bar)

        # ── Gemini star widget ──────────────────────────────────────────────
        self._star = GeminiStarWidget(size=80, parent=self._star_area)
        self._star.set_state("idle")
        self._star_area.resizeEvent = self._reposition_star   # hook

    def _reposition_star(self, event=None):
        """Keep the star centered in star_area as tile resizes."""
        sw, sh = self._star_area.width(), self._star_area.height()
        # Scale star proportionally to tile, clamped 60–120px
        target = max(60, min(120, int(min(sw, sh) * 0.45)))
        if self._star.width() != target:
            self._star.setFixedSize(target, target)
        x = (sw - self._star.width()) // 2
        y = (sh - self._star.height()) // 2
        self._star.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_star()

    # ── State setters ──────────────────────────────────────────────────────────

    def set_speaking(self, speaking: bool):
        self._speaking = speaking
        self._star.set_state("speaking" if speaking else "idle")
        self.setProperty("speaking", "true" if speaking else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        if speaking:
            self._set_status("SPEAKING", "#8ab4f8")
        else:
            self._set_status("IDLE", "#9aa0a6")

    def set_status(self, text: str, state: str = "idle"):
        """Called by signal: (label_text, state_key)"""
        colour_map = {
            "speaking": "#8ab4f8",
            "thinking": "#fbbc04",
            "acting":   "#34a853",
            "idle":     "#9aa0a6",
        }
        colour = colour_map.get(state, "#9aa0a6")
        self._star.set_state(state)
        self._set_status(text, colour)

    def set_thinking(self):
        self.set_status("THINKING", "thinking")

    def _set_status(self, text: str, colour: str):
        self._status_lbl.setText(text)
        self._status_lbl.setStyleSheet(
            f"color:{colour};font-size:10px;font-weight:600;"
            "background:rgba(0,0,0,0.55);border-radius:3px;padding:2px 6px;"
        )

    # ── Glow border ────────────────────────────────────────────────────────────

    def _tick_glow(self):
        if self._speaking:
            self._glow += 0.08 * self._glow_dir
            if self._glow >= 1.0:
                self._glow = 1.0; self._glow_dir = -1
            elif self._glow <= 0.4:
                self._glow = 0.4; self._glow_dir = 1
        else:
            self._glow = max(0.0, self._glow - 0.05)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Tile background
        p.setBrush(QBrush(QColor(0x3c, 0x40, 0x43)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 8, 8)

        # Speaking glow border
        if self._glow > 0:
            alpha = int(255 * self._glow)
            pen = QPen(QColor(138, 180, 248, alpha), 2.5)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)

        p.end()

    def mousePressEvent(self, event):
        self.clicked.emit(self.agent_name)
        super().mousePressEvent(event)
