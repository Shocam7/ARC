"""
LiveSession — Manages a Gemini Multimodal Live session for a single AF agent.
Handles real-time bidirectional audio streaming using google-genai SDK.
"""

import asyncio
import logging
import os
import base64
from typing import Callable, Awaitable

from google import genai
from google.genai import types as genai_types

logger = logging.getLogger("arc.live_session")

LIVE_MODEL = "gemini-2.0-flash-live-001"


class LiveSession:
    """
    Wraps a single Gemini Multimodal Live session.
    Runs on an asyncio event loop in a background thread.
    Streams microphone audio → Gemini → speaker audio.
    """

    def __init__(
        self,
        api_key: str,
        system_prompt: str,
        voice_name: str,
        tools: list,
        on_audio: Callable[[bytes], None],
        on_text: Callable[[str], None],
        on_tool_call: Callable[[str, dict], Awaitable[None]],
        on_speaking_start: Callable[[], None],
        on_speaking_end: Callable[[], None],
    ):
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.voice_name = voice_name
        self.tools = tools
        self.on_audio = on_audio
        self.on_text = on_text
        self.on_tool_call = on_tool_call
        self.on_speaking_start = on_speaking_start
        self.on_speaking_end = on_speaking_end

        self._client = genai.Client(api_key=api_key)
        self._session = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running = False
        self._send_queue: asyncio.Queue = None

    # ── Session lifecycle ─────────────────────────────────────────────────────

    async def _run(self):
        """Main async session loop."""
        self._send_queue = asyncio.Queue()

        config = genai_types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=genai_types.SpeechConfig(
                voice_config=genai_types.VoiceConfig(
                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                        voice_name=self.voice_name
                    )
                )
            ),
            system_instruction=genai_types.Content(
                parts=[genai_types.Part(text=self.system_prompt)],
                role="user"
            ),
            tools=self.tools if self.tools else None,
        )

        try:
            async with self._client.aio.live.connect(
                model=LIVE_MODEL,
                config=config
            ) as session:
                self._session = session
                logger.info(f"Live session connected (voice={self.voice_name})")

                # Run sender and receiver concurrently
                await asyncio.gather(
                    self._send_loop(),
                    self._recv_loop(),
                )
        except Exception as e:
            logger.error(f"Live session error: {e}")
        finally:
            self._session = None
            self._running = False
            logger.info("Live session closed")

    async def _send_loop(self):
        """Reads from send queue and streams to Gemini."""
        while self._running:
            try:
                item = await asyncio.wait_for(self._send_queue.get(), timeout=0.1)
                if item is None:
                    break
                kind, data = item
                if kind == "audio":
                    await self._session.send(
                        input=genai_types.LiveClientRealtimeInput(
                            media_chunks=[
                                genai_types.Blob(
                                    data=data,
                                    mime_type="audio/pcm;rate=16000"
                                )
                            ]
                        )
                    )
                elif kind == "text":
                    await self._session.send(
                        input=genai_types.LiveClientContent(
                            turns=[
                                genai_types.Content(
                                    parts=[genai_types.Part(text=data)],
                                    role="user"
                                )
                            ],
                            turn_complete=True
                        )
                    )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.warning(f"Send loop error: {e}")
                break

    async def _recv_loop(self):
        """Receives responses from Gemini and dispatches callbacks."""
        is_speaking = False
        try:
            async for response in self._session.receive():
                if not self._running:
                    break

                # ── Server content (audio/text) ──────────────
                if response.server_content:
                    if response.server_content.turn_complete:
                        if is_speaking:
                            is_speaking = False
                            self.on_speaking_end()
                        continue

                    for part in (response.server_content.model_turn.parts or []):
                        if part.inline_data:
                            # Audio response
                            if not is_speaking:
                                is_speaking = True
                                self.on_speaking_start()
                            self.on_audio(part.inline_data.data)
                        elif part.text:
                            self.on_text(part.text)

                # ── Tool call ────────────────────────────────
                if response.tool_call:
                    for fc in response.tool_call.function_calls:
                        asyncio.ensure_future(
                            self.on_tool_call(fc.name, dict(fc.args))
                        )

        except Exception as e:
            logger.error(f"Recv loop error: {e}")

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        """Start the session in the current event loop."""
        self._running = True
        return self._run()

    def send_audio(self, pcm_bytes: bytes):
        """Send a chunk of PCM audio from the microphone."""
        if self._send_queue and self._running:
            try:
                self._send_queue.put_nowait(("audio", pcm_bytes))
            except asyncio.QueueFull:
                pass

    def send_text(self, text: str):
        """Send a text message to the agent."""
        if self._send_queue and self._running:
            asyncio.run_coroutine_threadsafe(
                self._send_queue.put(("text", text)),
                self._loop
            )

    async def send_tool_result(self, function_call_id: str, result: str):
        """Send a tool result back to Gemini."""
        if self._session:
            await self._session.send(
                input=genai_types.LiveClientToolResponse(
                    function_responses=[
                        genai_types.FunctionResponse(
                            id=function_call_id,
                            name="tool_result",
                            response={"result": result}
                        )
                    ]
                )
            )

    def stop(self):
        """Stop the session."""
        self._running = False
        if self._send_queue:
            asyncio.run_coroutine_threadsafe(
                self._send_queue.put(None),
                self._loop
            )
