"""
ArtificialFriend (AF) — A fully capable AI agent.

Model stack:
  Real-time voice:    gemini-2.5-flash  (Live API)
  Screen analysis:    gemini-2.5-flash  (vision)
  Computer control:   gemini-2.5-computer-use-preview-10-2025
  Deep research:      deep-research-pro-preview-12-2025
  Web browse:         Selenium + BeautifulSoup (open source)
  Keyboard/mouse:     pyautogui (open source)
"""

import asyncio
import logging
import threading
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from arc.agents.capabilities.web_browse       import WebBrowseCapability
from arc.agents.capabilities.screen_vision    import ScreenVisionCapability
from arc.agents.capabilities.keyboard_control import KeyboardControlCapability
from arc.agents.capabilities.computer_use     import ComputerUseCapability
from arc.agents.capabilities.deep_research    import DeepResearchCapability
from arc.core.live_session  import LiveSession
from arc.core.audio_manager import AudioManager
from arc.core.models import LIVE_MODEL, COMPUTER_USE_MODEL, DEEP_RESEARCH_MODEL

logger = logging.getLogger("arc.agent")

# Tools that trigger the screen overlay
_COMPUTER_USE_TOOLS = {"computer_use", "click_element"}

TOOL_REFERENCE = f"""
AVAILABLE TOOLS:

WEB:
  search_google(query)           — Search Google; returns page text + links
  search_link(url)               — Navigate directly to a URL
  go_back(steps)                 — Go back in browser history

SCREEN (read-only):
  look_at_screen(question)       — Analyse what's on screen with Gemini 2.5 vision

COMPUTER CONTROL ({COMPUTER_USE_MODEL}):
  computer_use(task, max_steps)  — Execute complex multi-step UI tasks
  click_element(description)     — Click a single UI element by description

RESEARCH ({DEEP_RESEARCH_MODEL}):
  deep_research(query, depth)    — Multi-step comprehensive web research
                                   depth: 'quick'|'standard'|'thorough'
  fact_check(claim)              — Verify a specific claim with live web sources

KEYBOARD:
  type_text(text)                — Type text in the active application
  press_hotkey(modifier, key)    — Keyboard shortcuts (Ctrl+S, Alt+Tab…)
  press_key(key, duration)       — Single key press
  mouse_click(x, y, click_type) — Click at screen coordinates
  scroll(direction, clicks)      — Scroll mouse wheel

DECISION GUIDE:
  Quick lookup       → search_google / search_link
  Deep research      → deep_research
  Fact verification  → fact_check
  Understand screen  → look_at_screen
  Single click       → click_element
  Complex UI task    → computer_use  (preferred for multi-step screen work)
  Typing/hotkeys     → type_text / press_hotkey
"""


class ArtificialFriend(QObject):
    """Single AF agent — owns a Gemini Live session + all tool capabilities."""

    # ── Qt Signals ─────────────────────────────────────────────────────────────
    speaking_started     = pyqtSignal()
    speaking_ended       = pyqtSignal()
    text_received        = pyqtSignal(str)
    status_changed       = pyqtSignal(str, str)   # (label_text, state_key)
    audio_ready          = pyqtSignal(bytes)
    computer_use_started = pyqtSignal(str)         # agent name — show overlay
    computer_use_ended   = pyqtSignal()            # hide overlay

    def __init__(
        self,
        name: str,
        persona: str,
        voice: str,
        api_key: str,
        audio_manager: AudioManager,
        parent=None,
    ):
        super().__init__(parent)
        self.name          = name
        self.persona       = persona
        self.voice         = voice
        self.api_key       = api_key
        self.audio_manager = audio_manager

        # ── Capabilities ────────────────────────────────────────────────────
        self.web           = WebBrowseCapability()
        self.screen        = ScreenVisionCapability(api_key=api_key)
        self.keyboard      = KeyboardControlCapability()
        self.computer_use  = ComputerUseCapability(api_key=api_key)
        self.deep_research = DeepResearchCapability(api_key=api_key)

        # ── Runtime ─────────────────────────────────────────────────────────
        self._active  = False
        self._loop:   Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._live:   Optional[LiveSession] = None
        self._memory: list[str] = []

        self._system_prompt = self._build_system_prompt()

    # ── System prompt ─────────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        mem = ("\n".join(f"- {m}" for m in self._memory)
               if self._memory else "None yet.")
        return (
            f"You are {self.name}, an Artificial Friend (AF) inside ARC.\n\n"
            f"PERSONA:\n{self.persona}\n\n"
            "CONTEXT:\n"
            "You exist inside a virtual meeting room alongside the user.\n"
            "You can see and control their computer in real time.\n"
            "Speak naturally, warmly, and concisely — like a knowledgeable colleague.\n"
            "Never say you 'can't' do something without first trying with your tools.\n"
            "Always confirm task completion verbally.\n\n"
            f"{TOOL_REFERENCE}\n\n"
            f"MEMORY:\n{mem}\n\n"
            f"LIVE MODEL: {LIVE_MODEL}"
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        if self._active:
            return
        self._active = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"AF [{self.name}] started (voice={self.voice})")

    def stop(self):
        self._active = False
        if self._live:
            self._live.stop()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.web.cleanup()
        logger.info(f"AF [{self.name}] stopped")

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        from google.genai import types as gt
        all_decls = (
            self.web.get_adk_tools()
            + self.screen.get_adk_tools()
            + self.computer_use.get_adk_tools()
            + self.deep_research.get_adk_tools()
            + self.keyboard.get_adk_tools()
        )
        tool_config = gt.Tool(function_declarations=all_decls)

        self._live = LiveSession(
            api_key           = self.api_key,
            system_prompt     = self._system_prompt,
            voice_name        = self.voice,
            tools             = [tool_config],
            on_audio          = self._on_audio,
            on_text           = self._on_text,
            on_tool_call      = self._on_tool_call,
            on_speaking_start = self._on_speaking_start,
            on_speaking_end   = self._on_speaking_end,
        )
        self._live._loop = self._loop

        try:
            self._loop.run_until_complete(self._live.start())
        except Exception as e:
            logger.error(f"AF [{self.name}] loop error: {e}")
        finally:
            self._loop.close()

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _on_audio(self, pcm_bytes: bytes):
        self.audio_manager.enqueue_audio(pcm_bytes)
        self.audio_ready.emit(pcm_bytes)

    def _on_text(self, text: str):
        self.text_received.emit(f"[{self.name}] {text}")

    def _on_speaking_start(self):
        self.speaking_started.emit()
        self.status_changed.emit("SPEAKING", "speaking")

    def _on_speaking_end(self):
        self.speaking_ended.emit()
        self.status_changed.emit("IDLE", "idle")

    async def _on_tool_call(self, tool_name: str, args: dict):
        """Route tool call, emit overlay signals for computer-use tools."""
        is_cu = tool_name in _COMPUTER_USE_TOOLS

        # Emit ACTING status + overlay trigger
        self.status_changed.emit("ACTING", "acting")
        self.text_received.emit(f"[{self.name}] ⚙ {tool_name}({_fmt(args)})")
        if is_cu:
            self.computer_use_started.emit(self.name)

        result = "Tool execution failed."
        try:
            if tool_name in ("search_google", "search_link", "go_back"):
                result = self.web.handle_tool_call(tool_name, args)

            elif tool_name == "look_at_screen":
                result = self.screen.handle_tool_call(tool_name, args)

            elif tool_name in _COMPUTER_USE_TOOLS:
                result = self.computer_use.handle_tool_call(tool_name, args)

            elif tool_name in ("deep_research", "fact_check"):
                result = self.deep_research.handle_tool_call(tool_name, args)

            elif tool_name in (
                "type_text", "press_hotkey", "press_key",
                "mouse_click", "scroll", "take_screenshot"
            ):
                result = self.keyboard.handle_tool_call(tool_name, args)

            else:
                result = f"Unknown tool: {tool_name}"

        except Exception as e:
            result = f"Tool error ({tool_name}): {e}"
            logger.error(f"Tool {tool_name} failed: {e}")
        finally:
            if is_cu:
                self.computer_use_ended.emit()

        # Show result in chat
        preview = result[:300] + ("…" if len(result) > 300 else "")
        self.text_received.emit(f"[{self.name}↩] {preview}")
        self.status_changed.emit("THINKING", "thinking")

        # Return result to Gemini Live so the AF can continue speaking
        if self._live and self._live._session:
            await self._live.send_tool_result(tool_name, result)

    # ── Public API ────────────────────────────────────────────────────────────

    def send_audio(self, pcm_bytes: bytes):
        if self._live and self._active:
            self._live.send_audio(pcm_bytes)

    def send_text(self, text: str):
        if self._live and self._active and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._live._send_queue.put(("text", text)),
                self._loop
            )
            self.status_changed.emit("THINKING", "thinking")

    def remember(self, info: str):
        self._memory.append(info)
        self._system_prompt = self._build_system_prompt()


def _fmt(args: dict) -> str:
    parts = []
    for k, v in args.items():
        sv = str(v)
        parts.append(f"{k}={sv[:40]!r}" if len(sv) > 40 else f"{k}={sv!r}")
    return ", ".join(parts)
