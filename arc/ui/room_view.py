"""
RoomView — Google Meet–style meeting room.

Layout:
  • Full-window dark tile grid (auto-sizes to fill space like Meet)
  • Narrow chat panel slides in on the right
  • Slim bottom control bar
  • Header: time + room name (no title bar)

Tile behaviour mirrors Google Meet:
  1 tile  → centered, fills ~80% of space
  2 tiles → side by side 50/50
  3 tiles → top 2 + bottom 1 (centered)
  4 tiles → 2×2 grid
  5–6     → 2+3 or 3+3 rows
  7+      → 3-column grid
"""

import logging
import math
import cv2

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QFrame,
    QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QDateTime, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QColor, QBrush, QImage, QPixmap, QPainterPath

from arc.ui.agent_tile import AgentTile
from arc.ui.create_agent_dialog import CreateAgentDialog

logger = logging.getLogger("arc.ui.room")


# ── User webcam tile ──────────────────────────────────────────────────────────

class UserTile(QWidget):
    """Live webcam feed for the local user."""

    def __init__(self, username: str = "You", parent=None):
        super().__init__(parent)
        self.username = username
        self.setObjectName("meet_tile")
        self._pix  = None
        self._cap  = None
        self._muted   = False
        self._cam_off = False
        self._init_camera()

    def _init_camera(self):
        try:
            self._cap = cv2.VideoCapture(0)
            if self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
                t = QTimer(self)
                t.timeout.connect(self._grab)
                t.start(33)
        except Exception:
            pass

    def _grab(self):
        if not self._cap or not self._cap.isOpened() or self._cam_off:
            return
        ret, frame = self._cap.read()
        if not ret:
            return
        frame = cv2.flip(frame, 1)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self._pix = QPixmap.fromImage(img)
        self.update()

    def toggle_cam(self):
        self._cam_off = not self._cam_off
        self.update()

    def toggle_mute(self) -> bool:
        self._muted = not self._muted
        return self._muted

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Rounded clip
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 8, 8)
        p.setClipPath(path)

        # Background
        p.fillRect(self.rect(), QColor(0x3c, 0x40, 0x43))

        # Camera frame
        if self._pix and not self._cam_off:
            scaled = self._pix.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            ox = (scaled.width()  - self.width())  // 2
            oy = (scaled.height() - self.height()) // 2
            p.drawPixmap(-ox, -oy, scaled)
        else:
            # Placeholder initials
            init = self.username[0].upper() if self.username else "?"
            p.setPen(QColor(0x9a, 0xa0, 0xa6))
            from PyQt6.QtGui import QFont
            f = QFont("Segoe UI", int(min(self.width(), self.height()) * 0.22), QFont.Weight.Medium)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, init)

        # Name badge
        from PyQt6.QtGui import QFont
        badge_text = self.username + (" 🔇" if self._muted else "")
        p.setPen(QColor(0xff, 0xff, 0xff))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(badge_text) + 16
        th = fm.height() + 6
        badge_r = QRect(8, self.height() - th - 8, tw, th)
        p.setOpacity(0.7)
        p.setBrush(QBrush(QColor(0, 0, 0)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(badge_r, 4, 4)
        p.setOpacity(1.0)
        p.setPen(QColor(0xff, 0xff, 0xff))
        p.drawText(badge_r, Qt.AlignmentFlag.AlignCenter, badge_text)

        p.end()

    def cleanup(self):
        if self._cap:
            self._cap.release()


# ── Adaptive tile grid ────────────────────────────────────────────────────────

class MeetTileGrid(QWidget):
    """
    Auto-resizing grid that fills available space like Google Meet.
    All positioning is done manually in resizeEvent (no QLayout).
    """

    MARGIN = 12
    GAP    = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("room_view")
        self.setStyleSheet("background-color: #202124;")
        self._tiles: list[QWidget] = []

    def add_tile(self, tile: QWidget):
        tile.setParent(self)
        self._tiles.append(tile)
        tile.show()
        self._relayout()

    def remove_tile(self, tile: QWidget):
        if tile in self._tiles:
            self._tiles.remove(tile)
            tile.hide()
            tile.setParent(None)   # type: ignore[arg-type]
        self._relayout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self):
        n = len(self._tiles)
        if n == 0:
            return

        W = self.width()  - 2 * self.MARGIN
        H = self.height() - 2 * self.MARGIN
        g = self.GAP

        # ── Compute grid dimensions ──────────────────────────────────────────
        if n == 1:
            rows, cols = 1, 1
        elif n == 2:
            rows, cols = 1, 2
        elif n == 3:
            rows, cols = 1, 3
        elif n == 4:
            rows, cols = 2, 2
        elif n <= 6:
            rows, cols = 2, 3
        elif n <= 9:
            rows, cols = 3, 3
        else:
            cols = math.ceil(math.sqrt(n))
            rows = math.ceil(n / cols)

        tw = (W - g * (cols - 1)) // cols
        th = (H - g * (rows - 1)) // rows

        # Special single-tile: center with 16:9 if possible
        if n == 1:
            ideal_w = min(W, int(th * 16 / 9))
            ideal_h = min(H, int(tw *  9 / 16))
            tw = ideal_w
            th = ideal_h

        # ── Place tiles ──────────────────────────────────────────────────────
        for i, tile in enumerate(self._tiles):
            row, col = divmod(i, cols)
            # Centre last row if tiles don't fully fill it
            tiles_in_row = min(cols, n - row * cols)
            row_w_total  = tiles_in_row * tw + (tiles_in_row - 1) * g
            x_offset     = self.MARGIN + (W - row_w_total) // 2
            x = x_offset + col * (tw + g)
            y = self.MARGIN + row * (th + g)
            tile.setGeometry(x, y, tw, th)


# ── Chat / transcript panel ───────────────────────────────────────────────────

class ChatPanel(QWidget):
    message_sent = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chat_panel")
        self.setFixedWidth(300)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QLabel("In-call messages")
        hdr.setObjectName("chat_title")
        lay.addWidget(hdr)

        self._view = QTextEdit()
        self._view.setObjectName("chat_view")
        self._view.setReadOnly(True)
        lay.addWidget(self._view, 1)

        # Input
        inp_bar = QWidget()
        inp_bar.setObjectName("input_bar")
        inp_bar.setFixedHeight(60)
        il = QHBoxLayout(inp_bar)
        il.setContentsMargins(10, 10, 10, 10)
        il.setSpacing(8)

        self._input = QLineEdit()
        self._input.setObjectName("msg_input")
        self._input.setPlaceholderText("Message…")
        self._input.returnPressed.connect(self._send)

        send = QPushButton("➤")
        send.setObjectName("send_btn")
        send.clicked.connect(self._send)

        il.addWidget(self._input)
        il.addWidget(send)
        lay.addWidget(inp_bar)

    def _send(self):
        text = self._input.text().strip()
        if text:
            self.message_sent.emit(text)
            self._input.clear()

    def append(self, text: str):
        self._view.append(text)
        sb = self._view.verticalScrollBar()
        sb.setValue(sb.maximum())


# ── Control bar ───────────────────────────────────────────────────────────────

class MeetControlBar(QWidget):
    add_af_clicked   = pyqtSignal()
    mic_toggled      = pyqtSignal(bool)
    cam_toggled      = pyqtSignal(bool)
    chat_toggled     = pyqtSignal()
    end_call_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ctrl_bar")
        self.setFixedHeight(72)
        self._muted   = False
        self._cam_off = False
        self._elapsed = 0
        self._build()

        clk = QTimer(self)
        clk.timeout.connect(self._tick)
        clk.start(1000)

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(10)

        # Left: clock
        self._time_lbl = QLabel("00:00")
        self._time_lbl.setObjectName("room_time")
        lay.addWidget(self._time_lbl)
        lay.addStretch()

        # Centre controls
        self._mic_btn = self._round_btn("🎤")
        self._mic_btn.clicked.connect(self._tog_mic)

        self._cam_btn = self._round_btn("📷")
        self._cam_btn.clicked.connect(self._tog_cam)

        add_btn = QPushButton("+ Add AI Friend")
        add_btn.setObjectName("add_af_btn")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.add_af_clicked)

        end_btn = QPushButton("Leave")
        end_btn.setObjectName("end_btn")
        end_btn.clicked.connect(self.end_call_clicked)

        for w in [self._mic_btn, self._cam_btn, add_btn, end_btn]:
            lay.addWidget(w)
        lay.addStretch()

        # Right: chat toggle
        chat_btn = self._round_btn("💬")
        chat_btn.clicked.connect(self.chat_toggled)
        lay.addWidget(chat_btn)

    def _round_btn(self, icon: str) -> QPushButton:
        b = QPushButton(icon)
        b.setObjectName("ctrl_round")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        return b

    def _tick(self):
        self._elapsed += 1
        m, s = divmod(self._elapsed, 60)
        self._time_lbl.setText(f"{m:02d}:{s:02d}")

    def _tog_mic(self):
        self._muted = not self._muted
        self._mic_btn.setText("🔇" if self._muted else "🎤")
        self._mic_btn.setProperty("active", "false" if self._muted else "true")
        self.mic_toggled.emit(self._muted)

    def _tog_cam(self):
        self._cam_off = not self._cam_off
        self._cam_btn.setText("🚫" if self._cam_off else "📷")
        self.cam_toggled.emit(self._cam_off)


# ── Room view ─────────────────────────────────────────────────────────────────

class RoomView(QWidget):
    """Google Meet–style ARC meeting room."""

    leave_room            = pyqtSignal()
    agent_spawn_requested = pyqtSignal(dict)   # ← class-level signal (bug fixed)

    def __init__(self, room_name: str, username: str, orchestrator, parent=None):
        super().__init__(parent)
        self.room_name   = room_name
        self.username    = username
        self.orchestrator = orchestrator
        self.setObjectName("room_view")
        self.setStyleSheet("background-color: #202124;")

        self._agent_tiles: dict[str, AgentTile] = {}
        self._chat_visible = True
        self._overlay = None   # ScreenOverlayWindow (created on demand)

        self._build_ui()
        self.orchestrator.routing_decision.connect(self._on_routing)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Slim top bar ──────────────────────────────────────────────────────
        top = QWidget()
        top.setObjectName("room_header")
        top.setFixedHeight(44)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(16, 0, 16, 0)

        logo = QLabel("ARC")
        logo.setStyleSheet("color:#8ab4f8;font-size:15px;font-weight:700;")

        self._room_lbl = QLabel(self.room_name)
        self._room_lbl.setStyleSheet("color:#9aa0a6;font-size:13px;")

        self._orch_badge = QLabel("Orchestrator active")
        self._orch_badge.setObjectName("orch_banner")
        self._orch_badge.hide()

        tl.addWidget(logo)
        tl.addSpacing(12)
        tl.addWidget(self._room_lbl)
        tl.addStretch()
        tl.addWidget(self._orch_badge)
        root.addWidget(top)

        # ── Main area: tile grid + chat ───────────────────────────────────────
        mid = QHBoxLayout()
        mid.setContentsMargins(0, 0, 0, 0)
        mid.setSpacing(0)

        self._grid = MeetTileGrid()
        mid.addWidget(self._grid, 1)

        self._chat = ChatPanel()
        self._chat.message_sent.connect(self._on_message)
        mid.addWidget(self._chat)

        mid_widget = QWidget()
        mid_widget.setLayout(mid)
        root.addWidget(mid_widget, 1)

        # ── Control bar ───────────────────────────────────────────────────────
        self._ctrl = MeetControlBar()
        self._ctrl.add_af_clicked.connect(self._show_create_dialog)
        self._ctrl.end_call_clicked.connect(self.leave_room)
        self._ctrl.chat_toggled.connect(self._toggle_chat)
        self._ctrl.mic_toggled.connect(
            lambda muted: self._log("🎤 Muted" if muted else "🎤 Unmuted")
        )
        self._ctrl.cam_toggled.connect(
            lambda off: self._user_tile.toggle_cam() if hasattr(self, "_user_tile") else None
        )
        root.addWidget(self._ctrl)

        # Add user tile
        self._user_tile = UserTile(username=self.username)
        self._grid.add_tile(self._user_tile)

    # ── Chat visibility ────────────────────────────────────────────────────────

    def _toggle_chat(self):
        self._chat_visible = not self._chat_visible
        self._chat.setVisible(self._chat_visible)

    # ── Create AF dialog ───────────────────────────────────────────────────────

    def _show_create_dialog(self):
        dlg = CreateAgentDialog(self)
        dlg.agent_created.connect(self._spawn_agent)
        dlg.adjustSize()
        # Centre over this widget
        geo = self.geometry()
        dlg.move(
            self.mapToGlobal(self.rect().center()) - dlg.rect().center()
        )
        dlg.exec()

    def _spawn_agent(self, config: dict):
        name = config["name"]
        if name in self._agent_tiles:
            self._log(f"⚠ {name} already exists")
            return
        tile = AgentTile(agent_name=name, persona=config.get("persona", ""))
        tile.clicked.connect(lambda n: self._log(f"[{n}] selected"))
        self._agent_tiles[name] = tile
        self._grid.add_tile(tile)

        # Emit upward so MainWindow can create the actual AF agent
        self.agent_spawn_requested.emit(config)

        if self.orchestrator.agent_count >= 2:
            self._orch_badge.show()
        self._log(f"🤖 {name} joined the room")

    # ── Agent signal wiring ────────────────────────────────────────────────────

    def connect_agent_signals(self, agent):
        """Wire an AF's Qt signals to its tile + chat."""
        name = agent.name
        tile = self._agent_tiles.get(name)
        if not tile:
            return
        agent.speaking_started.connect(lambda: tile.set_speaking(True))
        agent.speaking_ended.connect(lambda: tile.set_speaking(False))
        agent.status_changed.connect(lambda t, s: tile.set_status(t, s))
        agent.text_received.connect(self._log)
        # Computer use overlay
        agent.computer_use_started.connect(
            lambda n=name: self._show_overlay(n)
        )
        agent.computer_use_ended.connect(self._hide_overlay)

    def remove_agent(self, name: str):
        tile = self._agent_tiles.pop(name, None)
        if tile:
            self._grid.remove_tile(tile)
        if self.orchestrator.agent_count < 2:
            self._orch_badge.hide()

    # ── Screen overlay ─────────────────────────────────────────────────────────

    def _show_overlay(self, agent_name: str):
        """Show the floating overlay during computer use."""
        from arc.ui.screen_overlay import ScreenOverlayWindow
        if self._overlay:
            self._overlay.cleanup()
        self._overlay = ScreenOverlayWindow(
            agent_name=agent_name,
            username=self.username
        )
        self._overlay.stop_requested.connect(self._on_overlay_stop)
        self._overlay.show()
        self._log(f"🖥 {agent_name} is now controlling the screen")

    def _hide_overlay(self):
        if self._overlay:
            self._overlay.cleanup()
            self._overlay = None
        self._log("✅ Screen control ended")

    def _on_overlay_stop(self):
        """User clicked Stop in the overlay."""
        self._hide_overlay()
        # TODO: signal the agent to abort current task
        self._log("⏹ Screen control stopped by user")

    # ── Input handling ─────────────────────────────────────────────────────────

    def _on_message(self, text: str):
        self._log(f"[You] {text}")
        target = self.orchestrator.dispatch_text(text)
        if target:
            tile = self._agent_tiles.get(target)
            if tile:
                tile.set_thinking()
        elif not self._agent_tiles:
            self._log("ℹ Add an AI Friend to start a conversation")

    def _on_routing(self, agent_name: str, reason: str):
        self._log(f"[→ {agent_name}] {reason}")

    def _log(self, text: str):
        self._chat.append(text)

    # ── Cleanup ────────────────────────────────────────────────────────────────

    def cleanup(self):
        self._user_tile.cleanup()
        if self._overlay:
            self._overlay.cleanup()
