"""
RoomView — The ARC meeting room.
Displays user tile + agent tiles in a responsive grid.
Houses the control bar, input bar, and transcript panel.
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit,
    QScrollArea, QSizePolicy, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QLinearGradient

from arc.ui.agent_tile import AgentTile
from arc.ui.user_tile import UserTile
from arc.ui.create_agent_dialog import CreateAgentDialog

logger = logging.getLogger("arc.ui.room")


class ScanlineOverlay(QWidget):
    """Subtle scanline effect painted over the room view for depth."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setOpacity(0.025)
        line_color = QColor(0, 200, 255)
        p.setPen(line_color)
        y = 0
        while y < self.height():
            p.drawLine(0, y, self.width(), y)
            y += 4
        p.end()


class TranscriptPanel(QWidget):
    """Side panel showing conversation transcript."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("transcript_panel")
        self.setFixedWidth(260)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("TRANSCRIPT")
        title.setObjectName("transcript_title")
        layout.addWidget(title)

        self._text = QTextEdit()
        self._text.setObjectName("transcript_view")
        self._text.setReadOnly(True)
        layout.addWidget(self._text)

    def append(self, text: str):
        self._text.append(text)
        # Auto-scroll to bottom
        sb = self._text.verticalScrollBar()
        sb.setValue(sb.maximum())


class ControlBar(QWidget):
    """Bottom control bar with mic, camera, add-AF and end-call buttons."""

    add_af_clicked   = pyqtSignal()
    mic_toggled      = pyqtSignal(bool)   # True = muted
    cam_toggled      = pyqtSignal(bool)   # True = cam off
    end_call_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("control_bar")
        self.setFixedHeight(72)
        self._muted = False
        self._cam_off = False
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)

        # ── Left: room info ──────────────────────────────────
        self._room_label = QLabel("ARC://ROOM")
        self._room_label.setStyleSheet(
            "color: #4a5a6e; font-size: 10px; letter-spacing: 3px;"
        )
        layout.addWidget(self._room_label)
        layout.addStretch()

        # ── Center: controls ─────────────────────────────────
        self._mic_btn = QPushButton("🎤")
        self._mic_btn.setObjectName("ctrl_btn")
        self._mic_btn.setToolTip("Toggle Microphone")
        self._mic_btn.clicked.connect(self._toggle_mic)

        self._cam_btn = QPushButton("📷")
        self._cam_btn.setObjectName("ctrl_btn")
        self._cam_btn.setToolTip("Toggle Camera")
        self._cam_btn.clicked.connect(self._toggle_cam)

        self._add_btn = QPushButton("+ ADD ARTIFICIAL FRIEND")
        self._add_btn.setObjectName("add_af_btn")
        self._add_btn.clicked.connect(self.add_af_clicked)

        self._end_btn = QPushButton("✕ END SESSION")
        self._end_btn.setObjectName("end_btn")
        self._end_btn.clicked.connect(self.end_call_clicked)

        for btn in [self._mic_btn, self._cam_btn]:
            layout.addWidget(btn)
        layout.addWidget(self._add_btn)
        layout.addWidget(self._end_btn)
        layout.addStretch()

        # ── Right: timer ─────────────────────────────────────
        self._timer_label = QLabel("00:00")
        self._timer_label.setStyleSheet(
            "color: #4a5a6e; font-size: 11px; letter-spacing: 3px; font-family: monospace;"
        )
        self._elapsed = 0
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick)
        self._clock.start(1000)
        layout.addWidget(self._timer_label)

    def _tick(self):
        self._elapsed += 1
        m, s = divmod(self._elapsed, 60)
        self._timer_label.setText(f"{m:02d}:{s:02d}")

    def _toggle_mic(self):
        self._muted = not self._muted
        self._mic_btn.setText("🔇" if self._muted else "🎤")
        self._mic_btn.setStyleSheet(
            "background-color: rgba(255,59,92,0.2); border-color: rgba(255,59,92,0.5);"
            if self._muted else ""
        )
        self.mic_toggled.emit(self._muted)

    def _toggle_cam(self):
        self._cam_off = not self._cam_off
        self._cam_btn.setText("🚫" if self._cam_off else "📷")
        self.cam_toggled.emit(self._cam_off)

    def set_room_name(self, name: str):
        self._room_label.setText(f"ARC://{name.upper()}")


class InputBar(QWidget):
    """Text input bar for sending messages to the AF(s)."""

    message_sent = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("input_bar")
        self.setFixedHeight(64)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(10)

        self._input = QLineEdit()
        self._input.setObjectName("text_input")
        self._input.setPlaceholderText("Message your Artificial Friend(s)...")
        self._input.returnPressed.connect(self._send)

        self._send_btn = QPushButton("➤")
        self._send_btn.setObjectName("send_btn")
        self._send_btn.clicked.connect(self._send)

        layout.addWidget(self._input)
        layout.addWidget(self._send_btn)

    def _send(self):
        text = self._input.text().strip()
        if text:
            self.message_sent.emit(text)
            self._input.clear()


class TileGrid(QWidget):
    """Responsive grid that holds all video tiles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tiles_container")
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(14)
        self._tiles: list[QWidget] = []

    def add_tile(self, tile: QWidget):
        self._tiles.append(tile)
        self._relayout()

    def remove_tile(self, tile: QWidget):
        if tile in self._tiles:
            self._tiles.remove(tile)
            tile.setParent(None)
            self._relayout()

    def _relayout(self):
        # Clear grid
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        n = len(self._tiles)
        if n == 0:
            return

        # Calculate optimal columns
        cols = 1 if n == 1 else (2 if n <= 4 else 3)
        for i, tile in enumerate(self._tiles):
            row, col = divmod(i, cols)
            self._layout.addWidget(tile, row, col)

        # Make tiles fill space equally
        for c in range(cols):
            self._layout.setColumnStretch(c, 1)


class RoomView(QWidget):
    """The main meeting room widget."""

    leave_room = pyqtSignal()

    def __init__(self, room_name: str, username: str, orchestrator, parent=None):
        super().__init__(parent)
        self.room_name = room_name
        self.username = username
        self.orchestrator = orchestrator
        self.setObjectName("room_view")
        self._agent_tiles: dict[str, AgentTile] = {}
        self._transcript = None
        self._init_ui()
        self._connect_orchestrator()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("header_bar")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(20, 0, 20, 0)

        logo = QLabel("ARC")
        logo.setObjectName("header_arc")
        dot = QLabel("●")
        dot.setObjectName("header_dot")

        room_label = QLabel(self.room_name.upper())
        room_label.setStyleSheet(
            "color: #8ba0b8; font-size: 11px; letter-spacing: 4px;"
        )

        self._orch_badge = QLabel("ORCHESTRATOR ACTIVE")
        self._orch_badge.setObjectName("orch_badge")
        self._orch_badge.hide()

        conn = QLabel("● CONNECTED")
        conn.setObjectName("connection_status")

        hdr_layout.addWidget(logo)
        hdr_layout.addWidget(dot)
        hdr_layout.addSpacing(10)
        hdr_layout.addWidget(room_label)
        hdr_layout.addStretch()
        hdr_layout.addWidget(self._orch_badge)
        hdr_layout.addSpacing(16)
        hdr_layout.addWidget(conn)

        root.addWidget(header)

        # ── Main area: grid + transcript ─────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: rgba(0,200,255,0.08); width: 1px; }")
        splitter.setHandleWidth(1)

        # Tile grid in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("root_bg")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        grid_container = QWidget()
        grid_container.setObjectName("root_bg")
        grid_vl = QVBoxLayout(grid_container)
        grid_vl.setContentsMargins(0, 0, 0, 0)
        grid_vl.setSpacing(0)

        self._tile_grid = TileGrid()
        grid_vl.addWidget(self._tile_grid)
        grid_vl.addStretch()

        scroll.setWidget(grid_container)
        splitter.addWidget(scroll)

        # Transcript panel
        self._transcript = TranscriptPanel()
        splitter.addWidget(self._transcript)
        splitter.setSizes([800, 260])

        root.addWidget(splitter, 1)

        # ── Input bar ─────────────────────────────────────────
        self._input_bar = InputBar()
        self._input_bar.message_sent.connect(self._on_message)
        root.addWidget(self._input_bar)

        # ── Control bar ───────────────────────────────────────
        self._ctrl_bar = ControlBar()
        self._ctrl_bar.set_room_name(self.room_name)
        self._ctrl_bar.add_af_clicked.connect(self._show_create_dialog)
        self._ctrl_bar.end_call_clicked.connect(self.leave_room)
        self._ctrl_bar.mic_toggled.connect(self._on_mic_toggle)
        root.addWidget(self._ctrl_bar)

        # Add user tile
        self._user_tile = UserTile(username=self.username)
        self._tile_grid.add_tile(self._user_tile)

        # Scanline overlay (cosmetic)
        self._scanline = ScanlineOverlay(self)
        self._scanline.resize(self.size())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._scanline.resize(self.size())

    def _connect_orchestrator(self):
        self.orchestrator.routing_decision.connect(self._on_routing)

    # ── AF Management ─────────────────────────────────────────────────────────

    def _show_create_dialog(self):
        dlg = CreateAgentDialog(self)
        dlg.agent_created.connect(self._spawn_agent)
        # Center on screen
        dlg.adjustSize()
        dlg.move(
            self.mapToGlobal(self.rect().center()) - dlg.rect().center()
        )
        dlg.exec()

    def _spawn_agent(self, config: dict):
        """Create a new AF tile and register with orchestrator."""
        name = config["name"]
        if name in self._agent_tiles:
            self._log(f"⚠ Agent {name} already exists.")
            return

        # Create tile
        tile = AgentTile(agent_name=name, persona=config.get("persona", ""))
        tile.clicked.connect(lambda n: self._log(f"[{n}] tile clicked"))
        self._agent_tiles[name] = tile
        self._tile_grid.add_tile(tile)

        # Signal room owner to create the actual agent
        # (RoomView emits upward; MainWindow/RoomSession handles agent creation)
        self.agent_spawn_requested.emit(config)

        # Update orchestrator badge
        if self.orchestrator.agent_count >= 2:
            self._orch_badge.show()

        self._log(f"🤖 Artificial Friend [{name}] joined the room")

    # Declare the signal (must be at class level; patched here for clarity)
    from PyQt6.QtCore import pyqtSignal as _sig
    agent_spawn_requested = _sig(dict)

    def connect_agent_signals(self, agent):
        """Wire an AF agent's signals to its tile and transcript."""
        name = agent.name
        tile = self._agent_tiles.get(name)
        if not tile:
            return
        agent.speaking_started.connect(lambda: tile.set_speaking(True))
        agent.speaking_ended.connect(lambda: tile.set_speaking(False))
        agent.status_changed.connect(lambda t, s: tile.set_status(t, s))
        agent.text_received.connect(self._log)

    def remove_agent(self, name: str):
        tile = self._agent_tiles.pop(name, None)
        if tile:
            self._tile_grid.remove_tile(tile)
        if self.orchestrator.agent_count < 2:
            self._orch_badge.hide()

    # ── Input handling ────────────────────────────────────────────────────────

    def _on_message(self, text: str):
        self._log(f"[YOU] {text}")
        target = self.orchestrator.dispatch_text(text)
        if target:
            tile = self._agent_tiles.get(target)
            if tile:
                tile.set_thinking()
        elif not self._agent_tiles:
            self._log("ℹ Add an Artificial Friend to start a conversation.")

    def _on_mic_toggle(self, muted: bool):
        self._log("🎤 Microphone muted" if muted else "🎤 Microphone active")

    def _on_routing(self, agent_name: str, reason: str):
        self._log(f"[ORCH → {agent_name}] {reason}")

    def _log(self, text: str):
        if self._transcript:
            self._transcript.append(text)

    def cleanup(self):
        self._user_tile.cleanup()
