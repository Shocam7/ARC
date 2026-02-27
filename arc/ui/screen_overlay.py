"""
ScreenOverlayWindow — Floating mini-tiles shown during computer use.

When an AF starts controlling the PC:
  • The main ARC window hides
  • This frameless overlay appears (always-on-top)
  • It shows small video tiles so the user can follow along
  • SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE) makes this window
    INVISIBLE to screenshots — Gemini's vision sees the clean desktop,
    not the overlay covering part of the screen.

WDA_EXCLUDEFROMCAPTURE = 0x11
  Works via Windows DXGI compositor and GDI BitBlt interception.
  Requires Windows 10 version 2004 (build 19041) or later.
"""

import logging
import sys
import cv2
import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QBrush, QPainterPath

from arc.ui.landing_page import GeminiStarWidget

logger = logging.getLogger("arc.screen_overlay")

# ── Windows API constants ─────────────────────────────────────────────────────
WDA_NONE               = 0x00000000
WDA_MONITOR            = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011   # Win10 2004+


def _apply_exclude_from_capture(hwnd: int):
    """
    Tell Windows to exclude this window from all screen captures.
    Safe to call on non-Windows (no-op).
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        result = ctypes.windll.user32.SetWindowDisplayAffinity(
            ctypes.c_void_p(hwnd),
            ctypes.c_uint(WDA_EXCLUDEFROMCAPTURE)
        )
        if result:
            logger.info(f"WDA_EXCLUDEFROMCAPTURE applied to HWND {hwnd:#010x}")
        else:
            err = ctypes.get_last_error()
            logger.warning(f"SetWindowDisplayAffinity failed (err={err})")
    except Exception as e:
        logger.warning(f"Could not apply WDA_EXCLUDEFROMCAPTURE: {e}")


# ── Mini cam widget ────────────────────────────────────────────────────────────

class MiniCamWidget(QWidget):
    """Small live webcam feed for the overlay."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 90)
        self._pix = None
        self._cap = None
        try:
            self._cap = cv2.VideoCapture(0)
            if self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  320)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                t = QTimer(self)
                t.timeout.connect(self._tick)
                t.start(40)
        except Exception:
            pass

    def _tick(self):
        if not self._cap or not self._cap.isOpened():
            return
        ret, frame = self._cap.read()
        if not ret:
            return
        frame = cv2.flip(frame, 1)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self._pix = QPixmap.fromImage(img).scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._pix:
            # Clip to rounded rect
            path = QPainterPath()
            path.addRoundedRect(0, 0, self.width(), self.height(), 6, 6)
            p.setClipPath(path)
            p.drawPixmap(0, 0, self._pix)
        else:
            p.fillRect(self.rect(), QColor(0x3c, 0x40, 0x43))
            p.setPen(QColor(0x9a, 0xa0, 0xa6))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "CAM")
        p.end()

    def cleanup(self):
        if self._cap:
            self._cap.release()


# ── Mini AF tile ───────────────────────────────────────────────────────────────

class MiniAFTile(QWidget):
    """Small version of an AF's Gemini star for the overlay."""

    def __init__(self, name: str, state: str = "acting", parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 90)
        self._name = name

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._star = GeminiStarWidget(size=52, parent=self)
        self._star.set_state(state)
        lay.addWidget(self._star, alignment=Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel(name)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            "color:#e8eaed;font-size:11px;font-weight:600;background:transparent;"
        )
        lay.addWidget(lbl)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 6, 6)
        p.setBrush(QBrush(QColor(0x3c, 0x40, 0x43)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)
        p.end()

    def set_state(self, state: str):
        self._star.set_state(state)


# ── Main overlay window ────────────────────────────────────────────────────────

class ScreenOverlayWindow(QWidget):
    """
    Frameless always-on-top window shown during computer use.
    Invisible to screen capture thanks to WDA_EXCLUDEFROMCAPTURE.
    """

    stop_requested = pyqtSignal()

    def __init__(self, agent_name: str, username: str = "You", parent=None):
        super().__init__(None)   # No Qt parent → separate OS window
        self.agent_name = agent_name
        self.username   = username

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint  |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(196)

        self._mini_af  = None
        self._mini_cam = None
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Container with rounded dark background
        container = QWidget()
        container.setStyleSheet("""
            background-color: rgba(32,33,36,0.92);
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.10);
        """)
        cl = QVBoxLayout(container)
        cl.setContentsMargins(10, 12, 10, 10)
        cl.setSpacing(8)

        # Header
        hdr = QLabel(f"🤖  {self.agent_name} is working…")
        hdr.setStyleSheet(
            "color:#e8eaed;font-size:11px;font-weight:600;background:transparent;"
        )
        hdr.setWordWrap(True)
        cl.addWidget(hdr)

        # AF mini tile
        self._mini_af = MiniAFTile(self.agent_name, state="acting")
        cl.addWidget(self._mini_af)

        # User mini cam
        self._mini_cam = MiniCamWidget()
        cl.addWidget(self._mini_cam)

        # Stop button
        stop = QPushButton("⏹  Stop")
        stop.setStyleSheet("""
            QPushButton {
                background-color: #ea4335;
                border: none;
                border-radius: 6px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
                padding: 8px;
            }
            QPushButton:hover { background-color: #c5221f; }
        """)
        stop.clicked.connect(self.stop_requested)
        cl.addWidget(stop)

        lay.addWidget(container)

    def showEvent(self, event):
        super().showEvent(event)
        # Position bottom-right of screen
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.right()  - self.width()  - 16,
            screen.bottom() - self.height() - 48
        )
        # Apply WDA_EXCLUDEFROMCAPTURE so this overlay is invisible to screenshots
        hwnd = int(self.winId())
        _apply_exclude_from_capture(hwnd)

    def set_agent_state(self, state: str):
        if self._mini_af:
            self._mini_af.set_state(state)

    def cleanup(self):
        if self._mini_cam:
            self._mini_cam.cleanup()
        self.close()
