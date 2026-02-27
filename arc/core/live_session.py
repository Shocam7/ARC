"""
LiveSession — Gemini Multimodal Live session for a single AF agent.

Backend: Vertex AI  (not AI Studio)
Model:   gemini-2.0-flash-live-preview-04-09
API:     v1beta1  (Live API is in beta on Vertex AI)

Authentication: Application Default Credentials (ADC)
  - No api_key needed
  - Run `gcloud auth application-default login` once, OR
  - Set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON path

Audio:
  Input:  16kHz PCM mono  (from mic)
  Output: 24kHz PCM mono  (to speakers)
"""

import asyncio
import logging
from typing import Callable, Awaitable

from google.genai.types import HttpOptions

from arc.core.models import LIVE_MODEL
from arc.core.vertex_config import get_project, get_location

logger = logging.getLogger("arc.live_session")


class LiveSession:
    """
    Wraps a single Gemini Multimodal Live session via Vertex AI.

    Differences from AI Studio version:
      • Client is created with vertexai=True + project/location (ADC auth)
      • HttpOptions(api_version="v1beta1") required for Live API on Vertex
      • No api_key parameter
    """

    def __init__(
        self,
        system_prompt: str,
        voice_name: str,
        tools: list,
        on_audio:          Callable[[bytes], None],
        on_text:           Callable[[str], None],
        on_tool_call:      Callable[[str, dict], Awaitable[None]],
        on_speaking_start: Callable[[], None],
        on_speaking_end:   Callable[[], None],
    ):
        self.system_prompt     = system_prompt
        self.voice_name        = voice_name
        self.tools             = tools
        self.on_audio          = on_audio
        self.on_text           = on_text
        self.on_tool_call      = on_tool_call
        self.on_speaking_start = on_speaking_start
        self.on_speaking_end   = on_speaking_end

        # Vertex AI client — ADC authentication, Live API endpoint
        from google import genai
        self._client = genai.Client(
            vertexai=True,
            project=get_project(),
            location=get_location(),
            http_options=HttpOptions(api_version="v1beta1"),
        )

        self._session    = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running    = False
        self._send_queue: asyncio.Queue | None = None

    # ── Session lifecycle ──────────────────────────────────────────────────────

    async def _run(self):
        from google.genai import types as gt

        self._send_queue = asyncio.Queue()

        config = gt.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=gt.SpeechConfig(
                voice_config=gt.VoiceConfig(
                    prebuilt_voice_config=gt.PrebuiltVoiceConfig(
                        voice_name=self.voice_name
                    )
                )
            ),
            system_instruction=gt.Content(
                parts=[gt.Part(text=self.system_prompt)],
                role="user",
            ),
            tools=self.tools if self.tools else None,
        )

        try:
            async with self._client.aio.live.connect(
                model=LIVE_MODEL,
                config=config,
            ) as session:
                self._session = session
                logger.info(
                    f"Vertex AI Live session connected "
                    f"[model={LIVE_MODEL}, voice={self.voice_name}]"
                )
                await asyncio.gather(
                    self._send_loop(),
                    self._recv_loop(),
                )
        except Exception as e:
            logger.error(f"Live session error: {e}")
        finally:
            self._session = None
            self._running = False

    # ── Send loop ─────────────────────────────────────────────────────────────

    async def _send_loop(self):
        from google.genai import types as gt

        while self._running:
            try:
                item = await asyncio.wait_for(self._send_queue.get(), timeout=0.1)
                if item is None:
                    break
                kind, data = item

                if kind == "audio":
                    await self._session.send(
                        input=gt.LiveClientRealtimeInput(
                            media_chunks=[
                                gt.Blob(data=data, mime_type="audio/pcm;rate=16000")
                            ]
                        )
                    )
                elif kind == "text":
                    await self._session.send(
                        input=gt.LiveClientContent(
                            turns=[gt.Content(
                                parts=[gt.Part(text=data)],
                                role="user",
                            )],
                            turn_complete=True,
                        )
                    )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.warning(f"Send loop error: {e}")
                break

    # ── Receive loop ──────────────────────────────────────────────────────────

    async def _recv_loop(self):
        is_speaking = False
        try:
            async for response in self._session.receive():
                if not self._running:
                    break

                if response.server_content:
                    sc = response.server_content
                    if sc.turn_complete:
                        if is_speaking:
                            is_speaking = False
                            self.on_speaking_end()
                        continue
                    if sc.model_turn:
                        for part in (sc.model_turn.parts or []):
                            if part.inline_data:
                                if not is_speaking:
                                    is_speaking = True
                                    self.on_speaking_start()
                                self.on_audio(part.inline_data.data)
                            elif part.text:
                                self.on_text(part.text)

                if response.tool_call:
                    for fc in response.tool_call.function_calls:
                        asyncio.ensure_future(
                            self.on_tool_call(fc.name, dict(fc.args))
                        )
        except Exception as e:
            logger.error(f"Recv loop error: {e}")

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self):
        """Return the coroutine that runs the session (run via event loop)."""
        self._running = True
        return self._run()

    def send_audio(self, pcm_bytes: bytes):
        """Non-blocking: enqueue mic audio for sending."""
        if self._send_queue and self._running:
            try:
                self._send_queue.put_nowait(("audio", pcm_bytes))
            except asyncio.QueueFull:
                pass

    def send_text(self, text: str):
        """Thread-safe text send from outside the asyncio loop."""
        if self._send_queue and self._running and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._send_queue.put(("text", text)),
                self._loop,
            )

    async def send_tool_result(self, tool_name: str, result: str):
        """Return a tool result to Gemini so the AF can continue speaking."""
        if not self._session:
            return
        from google.genai import types as gt
        try:
            await self._session.send(
                input=gt.LiveClientToolResponse(
                    function_responses=[
                        gt.FunctionResponse(
                            name=tool_name,
                            response={"result": result},
                        )
                    ]
                )
            )
        except Exception as e:
            logger.warning(f"Tool response send failed: {e}")

    def stop(self):
        """Signal the send loop to exit cleanly."""
        self._running = False
        if self._send_queue and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._send_queue.put(None),
                self._loop,
            )