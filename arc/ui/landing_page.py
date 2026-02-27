"""
LandingPage — Clean Google-style white entry screen with animated Gemini star.
"""
import math
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QBrush, QConicalGradient, QPainterPath, QPen


class GeminiStarWidget(QWidget):
    """Animated Gemini 4-pointed star. Reused by AgentTile too."""

    # Google brand colours
    BLUE   = QColor(66,  133, 244)
    RED    = QColor(234,  67,  53)
    YELLOW = QColor(251, 188,   4)
    GREEN  = QColor(52,  168,  83)

    def __init__(self, size: int = 80, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._phase      = 0.0   # gradient rotation angle
        self._pulse      = 0.0   # scale pulse
        self._opacity    = 1.0
        self._state      = "idle"
        self._timer      = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    # ── State API ─────────────────────────────────────────────────────────────
    def set_state(self, state: str):
        """state ∈ {'idle','speaking','thinking','acting'}"""
        self._state = state

    # ── Animation ─────────────────────────────────────────────────────────────
    def _tick(self):
        s = self._state
        if s == "speaking":
            self._phase = (self._phase + 4.0) % 360
            self._pulse  = (self._pulse + 0.10) % (2 * math.pi)
            self._opacity = 1.0
        elif s == "acting":
            self._phase = (self._phase + 2.5) % 360
            self._pulse  = (self._pulse + 0.14) % (2 * math.pi)
            self._opacity = 1.0
        elif s == "thinking":
            self._phase = (self._phase + 0.8) % 360
            self._pulse  = (self._pulse + 0.06) % (2 * math.pi)
            self._opacity = 0.75
        else:  # idle — slow drift
            self._phase = (self._phase + 0.4) % 360
            self._pulse  = 0.0
            self._opacity = 0.30
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw(p, self.width() / 2, self.height() / 2,
                   (min(self.width(), self.height()) / 2 - 3),
                   self._phase, self._pulse, self._opacity)
        p.end()

    @classmethod
    def _draw(cls, painter: QPainter, cx: float, cy: float,
              R: float, phase: float, pulse: float, opacity: float):
        """
        Static helper — also used by AgentTile to paint the star
        at arbitrary positions and sizes.
        """
        scale  = 1.0 + 0.07 * math.sin(pulse)
        R      = R * scale
        S      = R * 0.38       # waist factor — matches Gemini logo proportions

        path = QPainterPath()
        path.moveTo(cx,     cy - R)
        path.cubicTo(cx+S,  cy-R,  cx+R, cy-S,  cx+R, cy)
        path.cubicTo(cx+R,  cy+S,  cx+S, cy+R,  cx,   cy+R)
        path.cubicTo(cx-S,  cy+R,  cx-R, cy+S,  cx-R, cy)
        path.cubicTo(cx-R,  cy-S,  cx-S, cy-R,  cx,   cy-R)
        path.closeSubpath()

        grad = QConicalGradient(cx, cy, phase)
        grad.setColorAt(0.00, cls.BLUE)
        grad.setColorAt(0.25, cls.RED)
        grad.setColorAt(0.50, cls.YELLOW)
        grad.setColorAt(0.75, cls.GREEN)
        grad.setColorAt(1.00, cls.BLUE)

        painter.save()
        painter.setOpacity(opacity)
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
        painter.restore()


class LandingPage(QWidget):
    launch_room = pyqtSignal(str, str)   # (room_name, username)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("landing_page")
        self.setStyleSheet("QWidget#landing_page { background-color: #f8f9fa; }")
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Card
        card = QWidget()
        card.setFixedWidth(420)
        card.setStyleSheet("""
            background-color: #ffffff;
            border: 1px solid #e8eaed;
            border-radius: 16px;
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(52, 46, 52, 50)
        cl.setSpacing(0)

        # Animated star logo
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._star = GeminiStarWidget(size=72)
        self._star.set_state("speaking")   # Animate on landing
        row.addWidget(self._star)
        cl.addLayout(row)
        cl.addSpacing(18)

        # Title
        title = QLabel("ARC")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color:#202124;font-size:30px;font-weight:700;"
            "letter-spacing:-1px;background:transparent;"
        )
        cl.addWidget(title)
        cl.addSpacing(4)

        sub = QLabel("Artificial Reality Companion")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color:#5f6368;font-size:14px;background:transparent;")
        cl.addWidget(sub)
        cl.addSpacing(32)

        # Divider
        div = QWidget(); div.setFixedHeight(1)
        div.setStyleSheet("background:#e8eaed;")
        cl.addWidget(div)
        cl.addSpacing(28)

        # Your name
        cl.addWidget(self._lbl("Your name"))
        cl.addSpacing(6)
        self._name = QLineEdit("You")
        self._name.setObjectName("room_input")
        self._name.setFixedHeight(46)
        cl.addWidget(self._name)
        cl.addSpacing(18)

        # Room
        cl.addWidget(self._lbl("Room name"))
        cl.addSpacing(6)
        self._room = QLineEdit("My Room")
        self._room.setObjectName("room_input")
        self._room.setFixedHeight(46)
        self._room.returnPressed.connect(self._go)
        cl.addWidget(self._room)
        cl.addSpacing(30)

        # Button
        btn = QPushButton("Start new meeting")
        btn.setObjectName("launch_btn")
        btn.setFixedHeight(48)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._go)
        cl.addWidget(btn)
        cl.addSpacing(22)

        foot = QLabel("Powered by Gemini 2.5 · Google AI Studio")
        foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        foot.setStyleSheet("color:#bdc1c6;font-size:11px;background:transparent;")
        cl.addWidget(foot)

        outer.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

    def _lbl(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet("color:#5f6368;font-size:12px;font-weight:500;background:transparent;")
        return l

    def _go(self):
        room     = self._room.text().strip() or "My Room"
        username = self._name.text().strip() or "You"
        self.launch_room.emit(room, username)
