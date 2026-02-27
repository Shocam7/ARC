"""
MainWindow — ARC's top-level application window.
Manages navigation between landing page and room view.
Owns the AudioManager, Orchestrator, and all AF agents.

Authentication: Vertex AI ADC — no api_key stored or passed.
"""

import logging

from PyQt6.QtWidgets import QMainWindow, QStackedWidget
from PyQt6.QtCore import Qt, QTimer

from arc.ui.styles import LANDING_STYLESHEET, ROOM_STYLESHEET
from arc.ui.landing_page import LandingPage
from arc.ui.room_view import RoomView
from arc.agents.base_agent import ArtificialFriend
from arc.agents.orchestrator import Orchestrator
from arc.core.audio_manager import AudioManager

logger = logging.getLogger("arc.main_window")


class MainWindow(QMainWindow):
    """Top-level ARC window."""

    def __init__(self):
        """
        No api_key parameter — authentication handled by Vertex AI ADC.
        Credentials come from:
          • gcloud auth application-default login  (local dev)
          • GOOGLE_APPLICATION_CREDENTIALS env var  (service account)
        """
        super().__init__()
        self.setWindowTitle("ARC — Artificial Reality Companion")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        # Core services (all use ADC internally)
        self._audio  = AudioManager()
        self._orch   = Orchestrator()
        self._agents: dict[str, ArtificialFriend] = {}
        self._room:   RoomView | None = None
        self._mic_on = True

        # Mic → active agent @ 50Hz
        self._mic_timer = QTimer(self)
        self._mic_timer.timeout.connect(self._poll_mic)
        self._mic_timer.setInterval(20)

        # Page stack
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Landing page
        self._landing = LandingPage()
        self._landing.launch_room.connect(self._enter_room)
        self._stack.addWidget(self._landing)

        # Start with landing stylesheet
        self.setStyleSheet(LANDING_STYLESHEET)

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _enter_room(self, room_name: str, username: str):
        logger.info(f"Entering room: {room_name} as {username}")

        self._room = RoomView(
            room_name    = room_name,
            username     = username,
            orchestrator = self._orch,
        )
        self._room.leave_room.connect(self._leave_room)
        self._room.agent_spawn_requested.connect(self._spawn_agent)
        self._stack.addWidget(self._room)
        self._stack.setCurrentWidget(self._room)

        # Switch to dark room stylesheet
        self.setStyleSheet(ROOM_STYLESHEET)

        self._audio.start_mic()
        self._audio.start_playback()
        self._mic_timer.start()
        logger.info(f"Room [{room_name}] ready")

    def _leave_room(self):
        self._mic_timer.stop()
        self._audio.stop_mic()
        self._audio.stop_playback()

        for agent in list(self._agents.values()):
            agent.stop()
        self._agents.clear()

        if self._room:
            self._room.cleanup()
            self._stack.removeWidget(self._room)
            self._room.deleteLater()
            self._room = None

        # Back to light landing stylesheet
        self.setStyleSheet(LANDING_STYLESHEET)
        self._stack.setCurrentWidget(self._landing)

        # Reset orchestrator state
        for name in list(self._orch._agents.keys()):
            self._orch.unregister_agent(name)

    # ── Agent lifecycle ────────────────────────────────────────────────────────

    def _spawn_agent(self, config: dict):
        """Create, register, and start a new AF agent."""
        name = config["name"]
        if name in self._agents:
            logger.warning(f"Agent {name} already exists")
            return

        logger.info(f"Spawning AF: {name}")
        agent = ArtificialFriend(
            name          = name,
            persona       = config.get("persona", ""),
            voice         = config.get("voice", "Aoede"),
            audio_manager = self._audio,
            parent        = self,
        )
        self._agents[name] = agent
        self._orch.register_agent(agent)

        if self._room:
            self._room.connect_agent_signals(agent)

        try:
            agent.start()
            if self._room:
                self._room._log(f"✅ {name} is online (Vertex AI)")
        except Exception as e:
            logger.error(f"Failed to start {name}: {e}")
            if self._room:
                self._room._log(f"❌ {name} failed to start: {e}")

    # ── Mic polling ────────────────────────────────────────────────────────────

    def _poll_mic(self):
        if not self._mic_on:
            return
        chunk = self._audio.get_mic_chunk(timeout=0.01)
        if chunk:
            self._orch.dispatch_audio(chunk)

    # ── Cleanup ────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._mic_timer.stop()
        for agent in self._agents.values():
            agent.stop()
        self._audio.cleanup()
        if self._room:
            self._room.cleanup()
        super().closeEvent(event)