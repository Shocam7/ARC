"""
UserTile — The user's own webcam tile in the ARC meeting grid.
Captures frames from the default webcam and renders them via Qt.
"""

import cv2
import numpy as np

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont


class UserTile(QWidget):
    """Displays live webcam feed for the local user."""

    def __init__(self, username: str = "YOU", parent=None):
        super().__init__(parent)
        self.username = username
        self.setObjectName("user_tile")
        self.setMinimumSize(220, 190)
        self._cap = None
        self._frame_label = None
        self._muted = False
        self._cam_off = False
        self._init_ui()
        self._start_camera()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Camera frame display
        self._frame_label = QLabel()
        self._frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._frame_label.setStyleSheet(
            "background-color: #0a0e17; border-top-left-radius: 12px; border-top-right-radius: 12px;"
        )
        self._frame_label.setMinimumHeight(140)
        layout.addWidget(self._frame_label, 1)

        # Bottom bar
        bar = QWidget()
        bar.setStyleSheet(
            "background-color: rgba(7, 9, 15, 0.85); "
            "border-bottom-left-radius: 12px; border-bottom-right-radius: 12px;"
        )
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(12, 8, 12, 8)
        bar_layout.setSpacing(6)

        name_label = QLabel(self.username.upper())
        name_label.setObjectName("tile_name")

        amber_dot = QLabel("⬤")
        amber_dot.setStyleSheet("color: #ff9500; font-size: 8px; background: transparent;")

        you_label = QLabel("HOST")
        you_label.setObjectName("tile_status")

        bar_layout.addWidget(name_label)
        bar_layout.addStretch()
        bar_layout.addWidget(amber_dot)
        bar_layout.addWidget(you_label)

        layout.addWidget(bar)

    def _start_camera(self):
        try:
            self._cap = cv2.VideoCapture(0)
            if self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                self._timer = QTimer(self)
                self._timer.timeout.connect(self._update_frame)
                self._timer.start(33)  # ~30 fps
            else:
                self._show_placeholder("NO CAMERA")
        except Exception:
            self._show_placeholder("NO CAMERA")

    def _update_frame(self):
        if self._cap is None or not self._cap.isOpened():
            return
        ret, frame = self._cap.read()
        if not ret:
            return
        if self._cam_off:
            self._show_placeholder("CAM OFF")
            return

        frame = cv2.flip(frame, 1)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        qt_img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(qt_img)
        pix = pix.scaled(
            self._frame_label.width(), self._frame_label.height(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        self._frame_label.setPixmap(pix)

    def _show_placeholder(self, text: str):
        pix = QPixmap(self._frame_label.size())
        pix.fill(QColor("#0a0e17"))
        p = QPainter(pix)
        p.setPen(QColor(74, 90, 110))
        font = QFont("Consolas", 11)
        p.setFont(font)
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, text)
        p.end()
        self._frame_label.setPixmap(pix)

    def toggle_camera(self):
        self._cam_off = not self._cam_off

    def toggle_mute(self):
        self._muted = not self._muted
        return self._muted

    def cleanup(self):
        if self._cap and self._cap.isOpened():
            self._cap.release()
