"""
LandingPage — ARC's entrance screen.
User enters their name and room name before joining.
"""

import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient, QBrush


class GridBackground(QWidget):
    """Animated cyber-grid background."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._offset = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

    def _tick(self):
        self._offset = (self._offset + 0.4) % 60
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background gradient
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(7, 9, 15))
        grad.setColorAt(1, QColor(10, 14, 22))
        p.fillRect(0, 0, w, h, grad)

        # Scrolling grid lines
        pen = QPen(QColor(0, 200, 255, 12), 1)
        p.setPen(pen)
        cell = 60
        off = int(self._offset)

        # Vertical lines
        x = -(off % cell)
        while x < w:
            p.drawLine(int(x), 0, int(x), h)
            x += cell

        # Horizontal lines
        y = -(off % cell)
        while y < h:
            p.drawLine(0, int(y), w, int(y))
            y += cell

        # Glowing center cross
        cx, cy = w // 2, h // 2
        glow = QColor(0, 200, 255, 30)
        p.setPen(QPen(glow, 1))
        p.drawLine(cx, 0, cx, h)
        p.drawLine(0, cy, w, cy)

        # Corner accent brackets
        bracket_color = QColor(0, 200, 255, 45)
        p.setPen(QPen(bracket_color, 1.5))
        size = 30
        margin = 28
        corners = [
            (margin, margin, 1, 1),
            (w - margin, margin, -1, 1),
            (margin, h - margin, 1, -1),
            (w - margin, h - margin, -1, -1),
        ]
        for bx, by, dx, dy in corners:
            p.drawLine(bx, by, bx + dx * size, by)
            p.drawLine(bx, by, bx, by + dy * size)

        p.end()


class GlowingCircle(QWidget):
    """Pulsing glow sphere behind the logo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def _tick(self):
        self._phase += 0.06
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() // 2
        cy = self.height() // 2
        base_r = 120
        pulse = math.sin(self._phase) * 15
        r = int(base_r + pulse)

        # Multiple glow rings
        for i, (radius, alpha) in enumerate([
            (r + 60, 8), (r + 30, 18), (r, 35), (r - 20, 55)
        ]):
            glow = QColor(0, 150 + i * 15, 200 + i * 10, alpha)
            grad = QLinearGradient(cx - radius, cy, cx + radius, cy)
            grad.setColorAt(0, QColor(0, 0, 0, 0))
            grad.setColorAt(0.5, glow)
            grad.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(cx - radius, cy - radius // 2, radius * 2, radius)
        p.end()


class LandingPage(QWidget):
    """Landing / entry screen for ARC."""

    launch_room = pyqtSignal(str, str)  # (room_name, username)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("landing_page")
        self._init_ui()

    def _init_ui(self):
        # Background layers
        self._bg = GridBackground(self)
        self._bg.resize(self.size())

        self._glow = GlowingCircle(self)
        self._glow.setFixedSize(500, 300)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Center card
        card = QWidget()
        card.setFixedWidth(440)
        card.setStyleSheet("""
            background-color: rgba(13, 17, 23, 0.92);
            border: 1px solid rgba(0, 200, 255, 0.2);
            border-radius: 20px;
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(48, 44, 48, 44)
        card_layout.setSpacing(0)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo
        logo = QLabel("ARC")
        logo.setObjectName("arc_logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(logo)

        tagline = QLabel("ARTIFICIAL REALITY COMPANION")
        tagline.setObjectName("arc_tagline")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(tagline)

        card_layout.addSpacing(32)

        # Divider
        div = QLabel()
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(0,200,255,0.12);")
        card_layout.addWidget(div)

        card_layout.addSpacing(28)

        # Description
        desc = QLabel("Create a room and invite your Artificial Friends.")
        desc.setObjectName("landing_desc")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        card_layout.addSpacing(28)

        # Your name input
        name_label = QLabel("YOUR NAME")
        name_label.setStyleSheet("color: #4a5a6e; font-size: 10px; letter-spacing: 4px; margin-bottom: 6px;")
        card_layout.addWidget(name_label)

        self._name_input = QLineEdit()
        self._name_input.setObjectName("room_input")
        self._name_input.setPlaceholderText("Enter your name...")
        self._name_input.setText("USER")
        card_layout.addWidget(self._name_input)

        card_layout.addSpacing(14)

        # Room name input
        room_label = QLabel("ROOM ID")
        room_label.setStyleSheet("color: #4a5a6e; font-size: 10px; letter-spacing: 4px; margin-bottom: 6px;")
        card_layout.addWidget(room_label)

        self._room_input = QLineEdit()
        self._room_input.setObjectName("room_input")
        self._room_input.setPlaceholderText("Name your ARC room...")
        self._room_input.setText("NEXUS-1")
        card_layout.addWidget(self._room_input)

        card_layout.addSpacing(28)

        # Launch button
        self._launch_btn = QPushButton("ENTER THE ARC")
        self._launch_btn.setObjectName("launch_btn")
        self._launch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._launch_btn.clicked.connect(self._on_launch)
        card_layout.addWidget(self._launch_btn)

        card_layout.addSpacing(20)

        # Version label
        version = QLabel("v1.0 · POWERED BY GEMINI 2.0 LIVE")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("color: #2a3a4e; font-size: 9px; letter-spacing: 2px;")
        card_layout.addWidget(version)

        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_bg'):
            self._bg.resize(self.size())
        if hasattr(self, '_glow'):
            self._glow.move(
                (self.width() - self._glow.width()) // 2,
                (self.height() - self._glow.height()) // 2 - 60
            )

    def _on_launch(self):
        room = self._room_input.text().strip() or "NEXUS-1"
        username = self._name_input.text().strip() or "USER"
        self.launch_room.emit(room, username)
