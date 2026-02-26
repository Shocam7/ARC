"""
MainWindow — ARC's top-level application window.
Manages navigation between landing page and room view.
Owns the AudioManager, Orchestrator, and all AF agents.
"""

import asyncio
import logging
import os
import threading

from PyQt6.QtWidgets import QMainWindow, QWidget, QStackedWidget, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon

from arc.ui.styles import ARC_STYLESHEET
from arc.ui.landing_page import LandingPage
from arc.ui.room_view import RoomView
from arc.agents.base_agent import ArtificialFriend
from arc.agents.orchestrator import Orchestrator
from arc.core.audio_manager import AudioManager

logger = logging.getLogger("arc.main_window")


class MainWindow(QMainWindow):
    """Top-level ARC window."""

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.setWindowTitle("ARC — Artificial Reality Companion")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)

        # Apply global stylesheet
        self.setStyleSheet(ARC_STYLESHEET)

        # Core services
        self._audio_manager = AudioManager()
        self._orchestrator = Orchestrator(api_key=api_key)
        self._agents: dict[str, ArtificialFriend] = {}
        self._room_view: RoomView | None = None
        self._mic_active = True

        # Mic polling timer (sends audio to active agent)
        self._mic_timer = QTimer(self)
        self._mic_timer.timeout.connect(self._poll_mic)
        self._mic_timer.setInterval(20)  # 50Hz

        # Stack: 0=landing, 1=room
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Landing page
        self._landing = LandingPage()
        self._landing.launch_room.connect(self._enter_room)
        self._stack.addWidget(self._landing)

        # Set style hints
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _enter_room(self, room_name: str, username: str):
        """Transition from landing page to the meeting room."""
        logger.info(f"Entering room: {room_name} as {username}")

        # Create room view
        self._room_view = RoomView(
            room_name=room_name,
            username=username,
            orchestrator=self._orchestrator,
        )
        self._room_view.leave_room.connect(self._leave_room)
        self._room_view.agent_spawn_requested.connect(self._spawn_agent)
        self._stack.addWidget(self._room_view)
        self._stack.setCurrentWidget(self._room_view)

        # Start audio
        self._audio_manager.start_mic()
        self._audio_manager.start_playback()
        self._mic_timer.start()

        logger.info(f"Room [{room_name}] entered")

    def _leave_room(self):
        """Stop everything and return to landing page."""
        self._mic_timer.stop()
        self._audio_manager.stop_mic()
        self._audio_manager.stop_playback()

        # Stop all agents
        for agent in list(self._agents.values()):
            agent.stop()
        self._agents.clear()

        if self._room_view:
            self._room_view.cleanup()
            self._stack.removeWidget(self._room_view)
            self._room_view.deleteLater()
            self._room_view = None

        self._stack.setCurrentWidget(self._landing)
        # Clear orchestrator state
        for name in list(self._orchestrator._agents.keys()):
            self._orchestrator.unregister_agent(name)

    # ── Agent lifecycle ────────────────────────────────────────────────────────

    def _spawn_agent(self, config: dict):
        """Create, register, and start a new AF agent."""
        name = config["name"]
        if name in self._agents:
            logger.warning(f"Agent {name} already exists")
            return

        # Check API key
        if not self.api_key:
            if self._room_view:
                self._room_view._log("❌ No GEMINI_API_KEY found. Set it in your .env file.")
            return

        logger.info(f"Spawning AF: {name}")

        agent = ArtificialFriend(
            name=name,
            persona=config.get("persona", ""),
            voice=config.get("voice", "Aoede"),
            api_key=self.api_key,
            audio_manager=self._audio_manager,
            parent=self,
        )

        self._agents[name] = agent
        self._orchestrator.register_agent(agent)

        # Wire signals to room view
        if self._room_view:
            self._room_view.connect_agent_signals(agent)

        # Start the agent (launches its asyncio loop in a daemon thread)
        try:
            agent.start()
            if self._room_view:
                self._room_view._log(f"✅ AF [{name}] online and ready")
        except Exception as e:
            logger.error(f"Failed to start AF [{name}]: {e}")
            if self._room_view:
                self._room_view._log(f"❌ Failed to start AF [{name}]: {e}")

    # ── Mic polling ────────────────────────────────────────────────────────────

    def _poll_mic(self):
        """Send buffered mic audio to the active agent via orchestrator."""
        if not self._mic_active:
            return
        chunk = self._audio_manager.get_mic_chunk(timeout=0.01)
        if chunk:
            self._orchestrator.dispatch_audio(chunk)

    # ── Cleanup ────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._mic_timer.stop()
        for agent in self._agents.values():
            agent.stop()
        self._audio_manager.cleanup()
        if self._room_view:
            self._room_view.cleanup()
        super().closeEvent(event)
