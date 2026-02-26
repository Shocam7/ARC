"""
AudioManager — Handles microphone capture and speaker playback.
Uses PyAudio for real-time audio I/O, compatible with Gemini Live API.
"""

import asyncio
import threading
import queue
import logging

logger = logging.getLogger("arc.audio")

# Gemini Live API audio format requirements
SAMPLE_RATE_IN  = 16000   # 16kHz input
SAMPLE_RATE_OUT = 24000   # 24kHz output
CHANNELS        = 1
FORMAT_BYTES    = 2       # int16
CHUNK_SIZE      = 1024

try:
    import pyaudio
    _PA_AVAILABLE = True
except ImportError:
    _PA_AVAILABLE = False
    logger.warning("PyAudio not available — audio I/O disabled")


class AudioManager:
    """
    Manages microphone input (for sending to Gemini Live)
    and speaker output (for playing Gemini Live audio responses).
    """

    def __init__(self):
        self._pa = None
        self._mic_stream = None
        self._spk_stream = None
        self._mic_queue: queue.Queue[bytes] = queue.Queue()
        self._recording = False
        self._playing = False
        self._play_queue: queue.Queue[bytes] = queue.Queue()
        self._play_thread: threading.Thread | None = None
        self._mic_thread: threading.Thread | None = None

        if _PA_AVAILABLE:
            try:
                self._pa = pyaudio.PyAudio()
            except Exception as e:
                logger.error(f"PyAudio init failed: {e}")

    # ── Microphone ────────────────────────────────────────────────────────────

    def start_mic(self):
        """Start capturing microphone audio."""
        if not self._pa or self._recording:
            return
        self._recording = True
        self._mic_thread = threading.Thread(target=self._mic_loop, daemon=True)
        self._mic_thread.start()

    def stop_mic(self):
        """Stop microphone capture."""
        self._recording = False

    def _mic_loop(self):
        try:
            stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE_IN,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
            )
            while self._recording:
                try:
                    data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    self._mic_queue.put(data)
                except Exception:
                    pass
            stream.stop_stream()
            stream.close()
        except Exception as e:
            logger.error(f"Mic stream error: {e}")

    def get_mic_chunk(self, timeout: float = 0.05) -> bytes | None:
        """Non-blocking read of the latest microphone chunk."""
        try:
            return self._mic_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def drain_mic_queue(self):
        """Clear buffered mic data."""
        while not self._mic_queue.empty():
            try:
                self._mic_queue.get_nowait()
            except queue.Empty:
                break

    # ── Speaker ───────────────────────────────────────────────────────────────

    def start_playback(self):
        """Start speaker playback loop."""
        if not self._pa or self._playing:
            return
        self._playing = True
        self._play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self._play_thread.start()

    def stop_playback(self):
        """Stop speaker playback."""
        self._playing = False

    def enqueue_audio(self, pcm_data: bytes):
        """Queue PCM audio data for playback."""
        self._play_queue.put(pcm_data)

    def _play_loop(self):
        try:
            stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE_OUT,
                output=True,
                frames_per_buffer=CHUNK_SIZE,
            )
            while self._playing:
                try:
                    data = self._play_queue.get(timeout=0.05)
                    stream.write(data)
                except queue.Empty:
                    pass
            stream.stop_stream()
            stream.close()
        except Exception as e:
            logger.error(f"Playback stream error: {e}")

    def clear_playback(self):
        """Flush the playback queue (e.g. when agent is interrupted)."""
        while not self._play_queue.empty():
            try:
                self._play_queue.get_nowait()
            except queue.Empty:
                break

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def cleanup(self):
        self._recording = False
        self._playing = False
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
