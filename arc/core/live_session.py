"""
ScreenVisionCapability — Screenshot analysis using gemini-2.5-flash.

Upgraded from gemini-2.0-flash:
- Better spatial understanding and UI element recognition
- Improved OCR of on-screen text
- More reliable bounding box coordinates for element location
"""

import base64
import io
import logging
from typing import Optional

logger = logging.getLogger("arc.capabilities.screen")

try:
    import pygetwindow as gw
    from PIL import ImageGrab
    _SCREEN_AVAILABLE = True
except ImportError:
    _SCREEN_AVAILABLE = False
    logger.warning("PIL/pygetwindow not available — screen vision disabled")

from arc.core.models import VISION_MODEL


def _capture_jpeg(quality: int = 82) -> Optional[tuple[bytes, int, int]]:
    if not _SCREEN_AVAILABLE:
        return None
    try:
        win = gw.getActiveWindow()
        bbox = (win.left, win.top, win.left + win.width, win.top + win.height) if win else None
        img = ImageGrab.grab(bbox=bbox)
        w, h = img.size
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=quality)
        return buf.getvalue(), w, h
    except Exception as e:
        logger.error(f"Capture failed: {e}")
        return None


class ScreenVisionCapability:
    """
    Analyses screenshots with gemini-2.5-flash.
    For interactive screen control (clicking, typing) use ComputerUseCapability.
    This capability is for read-only understanding of screen content.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None
        if api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.error(f"Vision client init failed: {e}")

    def look_at_screen(self, question: str = "What do you see?") -> str:
        """
        Capture the active window and analyse it with gemini-2.5-flash.

        Args:
            question: What to look for or describe on screen.
        Returns:
            Detailed description relevant to the question.
        """
        if not _SCREEN_AVAILABLE:
            return "Screen capture not available."
        capture = _capture_jpeg()
        if not capture:
            return "Could not capture screen."
        jpeg_bytes, w, h = capture

        if not self._client:
            return "Vision model not available."

        try:
            from google.genai import types as gt
            img_b64 = base64.b64encode(jpeg_bytes).decode()
            win_title = gw.getActiveWindowTitle() or "unknown"
            response = self._client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    gt.Part(inline_data=gt.Blob(data=img_b64, mime_type="image/jpeg")),
                    gt.Part(text=(
                        f"Active window: {win_title}\n"
                        f"Question: {question}\n\n"
                        "Describe what you see in detail, focusing on answering the question. "
                        "Include: application name, key UI elements, visible text content, "
                        "and any relevant details. Be thorough but concise."
                    )),
                ],
                config={"temperature": 0.2, "max_output_tokens": 1024}
            )
            return response.text or "No description available."
        except Exception as e:
            logger.error(f"Vision failed: {e}")
            return f"Vision error: {e}"

    def get_active_window_title(self) -> str:
        if not _SCREEN_AVAILABLE:
            return "unknown"
        try:
            return gw.getActiveWindowTitle() or "unknown"
        except Exception:
            return "unknown"

    def get_adk_tools(self) -> list:
        from google.genai import types as gt
        return [
            gt.FunctionDeclaration(
                name="look_at_screen",
                description=(
                    "Take a screenshot of the active window and analyse what's on screen "
                    "using Gemini 2.5 Flash vision. Use this to understand the current "
                    "state of the user's computer before deciding what to do."
                ),
                parameters=gt.Schema(
                    type=gt.Type.OBJECT,
                    properties={
                        "question": gt.Schema(
                            type=gt.Type.STRING,
                            description="What to look for or analyse on the screen"
                        )
                    }
                )
            ),
        ]

    def handle_tool_call(self, name: str, args: dict) -> str:
        if name == "look_at_screen":
            return self.look_at_screen(args.get("question", "What do you see?"))
        return f"Unknown screen tool: {name}"
