"""
ArtificialFriend (AF) — A fully capable AI agent.
Combines Gemini Multimodal Live for real-time voice interaction
with Jayu's tool capabilities (web, screen, keyboard).
"""

import asyncio
import logging
import os
import threading
from typing import Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from arc.agents.capabilities.web_browse import WebBrowseCapability
from arc.agents.capabilities.screen_vision import ScreenVisionCapability
from arc.agents.capabilities.keyboard_control import KeyboardControlCapability
from arc.core.live_session import LiveSession
from arc.core.audio_manager import AudioManager

logger = logging.getLogger("arc.agent")


BASE_CAPABILITY_INSTRUCTIONS = """
You have access to powerful tools to help the user:

AVAILABLE TOOLS:
• search_google(query) — Search Google for information
• search_link(url) — Navigate directly to a URL  
• go_back(steps) — Go back in browser history
• look_at_screen(question) — Analyze what's on the user's screen
• find_and_click_element(element_description, click_type) — Click a UI element on screen
• type_text(text) — Type text using the keyboard
• press_hotkey(modifier, key) — Press keyboard shortcuts (Ctrl+C, Alt+Tab, etc.)
• press_key(key, duration) — Press individual keys
• mouse_click(x, y, click_type) — Click at screen coordinates
• scroll(direction, clicks) — Scroll the mouse wheel

When the user asks you to do something on their computer, use these tools proactively.
Always confirm when you've completed a task.
Be concise in verbal responses — save detail for when it's needed.
"""


class ArtificialFriend(QObject):
    """
    A single AF agent instance.
    Manages its own Live session, audio I/O, and tool capabilities.
    """

    # ── Qt Signals ─────────────────────────────────────────────────────────────
    speaking_started  = pyqtSignal()
    speaking_ended    = pyqtSignal()
    text_received     = pyqtSignal(str)       # transcript text
    status_changed    = pyqtSignal(str, str)  # (status_text, state_key)
    audio_ready       = pyqtSignal(bytes)     # raw PCM from Gemini

    def __init__(
        self,
        name: str,
        persona: str,
        voice: str,
        api_key: str,
        audio_manager: AudioManager,
        parent=None
    ):
        super().__init__(parent)
        self.name = name
        self.persona = persona
        self.voice = voice
        self.api_key = api_key
        self.audio_manager = audio_manager

        # ── Capabilities ────────────────────────────────────
        self.web = WebBrowseCapability()
        self.screen = ScreenVisionCapability(api_key=api_key)
        self.keyboard = KeyboardControlCapability()

        # ── State ────────────────────────────────────────────
        self._active = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._live_session: Optional[LiveSession] = None
        self._memory: list[str] = []  # persistent memory strings

        # Build full system prompt
        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return f"""
You are {self.name}, an Artificial Friend (AF) inside ARC — Artificial Reality Companion.

PERSONALITY & PERSONA:
{self.persona}

CONTEXT:
You exist inside a virtual meeting room called ARC alongside the user.
You can see and interact with their computer in real time.
You speak naturally, warmly, and concisely.
You never say you "can't" do something without first trying with your tools.

{BASE_CAPABILITY_INSTRUCTIONS}

MEMORY: {', '.join(self._memory) if self._memory else 'No memories yet.'}
""".strip()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        """Start the agent's async event loop and Live session."""
        if self._active:
            return
        self._active = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"AF [{self.name}] started")

    def stop(self):
        """Stop the agent."""
        self._active = False
        if self._live_session:
            self._live_session.stop()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.web.cleanup()
        logger.info(f"AF [{self.name}] stopped")

    def _run_loop(self):
        """Runs the asyncio event loop for this agent."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        # Build tools list from all capabilities
        all_tools = (
            self.web.get_adk_tools()
            + self.screen.get_adk_tools()
            + self.keyboard.get_adk_tools()
        )

        from google.genai import types as genai_types
        tool_config = genai_types.Tool(function_declarations=all_tools)

        self._live_session = LiveSession(
            api_key=self.api_key,
            system_prompt=self._system_prompt,
            voice_name=self.voice,
            tools=[tool_config],
            on_audio=self._on_audio,
            on_text=self._on_text,
            on_tool_call=self._on_tool_call,
            on_speaking_start=self._on_speaking_start,
            on_speaking_end=self._on_speaking_end,
        )
        self._live_session._loop = self._loop

        try:
            self._loop.run_until_complete(self._live_session.start())
        except Exception as e:
            logger.error(f"AF [{self.name}] loop error: {e}")
        finally:
            self._loop.close()

    # ── Callbacks from LiveSession ────────────────────────────────────────────

    def _on_audio(self, pcm_bytes: bytes):
        """Gemini returned audio — play it."""
        self.audio_manager.enqueue_audio(pcm_bytes)
        self.audio_ready.emit(pcm_bytes)

    def _on_text(self, text: str):
        """Gemini returned text (transcript)."""
        self.text_received.emit(f"[{self.name}] {text}")
        logger.debug(f"AF [{self.name}] text: {text[:80]}")

    def _on_speaking_start(self):
        self.speaking_started.emit()
        self.status_changed.emit("SPEAKING", "speaking")
        logger.debug(f"AF [{self.name}] speaking started")

    def _on_speaking_end(self):
        self.speaking_ended.emit()
        self.status_changed.emit("IDLE", "idle")
        logger.debug(f"AF [{self.name}] speaking ended")

    async def _on_tool_call(self, tool_name: str, args: dict):
        """Dispatch tool calls to the correct capability."""
        self.status_changed.emit("ACTING", "acting")
        logger.info(f"AF [{self.name}] tool call: {tool_name}({args})")

        result = "Tool execution failed."
        try:
            # Route to the right capability
            if tool_name in ("search_google", "search_link", "go_back"):
                result = self.web.handle_tool_call(tool_name, args)
            elif tool_name in ("look_at_screen", "find_and_click_element"):
                result = self.screen.handle_tool_call(tool_name, args)
            elif tool_name in ("type_text", "press_hotkey", "press_key",
                               "mouse_click", "scroll", "take_screenshot"):
                result = self.keyboard.handle_tool_call(tool_name, args)
            else:
                result = f"Unknown tool: {tool_name}"
        except Exception as e:
            result = f"Tool error: {e}"
            logger.error(f"Tool {tool_name} failed: {e}")

        self.text_received.emit(f"[{self.name}→{tool_name}] {result[:200]}")
        self.status_changed.emit("THINKING", "thinking")

        # Send result back to the live session
        if self._live_session and self._live_session._session:
            try:
                from google.genai import types as genai_types
                await self._live_session._session.send(
                    input=genai_types.LiveClientToolResponse(
                        function_responses=[
                            genai_types.FunctionResponse(
                                name=tool_name,
                                response={"result": result}
                            )
                        ]
                    )
                )
            except Exception as e:
                logger.warning(f"Tool response send failed: {e}")

    # ── Public interaction API ────────────────────────────────────────────────

    def send_audio(self, pcm_bytes: bytes):
        """Feed microphone audio to this agent."""
        if self._live_session and self._active:
            self._live_session.send_audio(pcm_bytes)

    def send_text(self, text: str):
        """Send a text message to this agent."""
        if self._live_session and self._active and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._live_session._send_queue.put(("text", text)),
                self._loop
            )
            self.status_changed.emit("THINKING", "thinking")

    def remember(self, info: str):
        """Store a memory for this agent."""
        self._memory.append(info)
        # Rebuild system prompt with updated memory
        self._system_prompt = self._build_system_prompt()
