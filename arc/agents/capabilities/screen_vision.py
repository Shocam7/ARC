"""
ScreenVision capability — Screenshot analysis using Gemini Flash.
"""

import base64
import logging
import os
from typing import Optional

logger = logging.getLogger("arc.capabilities.screen")

try:
    import pyautogui
    from PIL import ImageGrab
    import pygetwindow as gw
    _SCREEN_AVAILABLE = True
except ImportError:
    _SCREEN_AVAILABLE = False
    logger.warning("pyautogui/PIL not available — screen vision disabled")


def _capture_active_window() -> Optional[bytes]:
    """Capture the currently active window as JPEG bytes."""
    if not _SCREEN_AVAILABLE:
        return None
    try:
        win = gw.getActiveWindow()
        if win:
            img = ImageGrab.grab(bbox=(
                win.left, win.top,
                win.left + win.width,
                win.top + win.height
            ))
        else:
            img = ImageGrab.grab()
        # Convert to JPEG bytes
        import io
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=80)
        return buf.getvalue()
    except Exception as e:
        logger.error(f"Screen capture failed: {e}")
        return None


class ScreenVisionCapability:
    """
    Provides screen analysis tools for an AF agent.
    Uses Gemini Flash vision to understand and describe screen content.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None
        if api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.error(f"Failed to init Gemini client: {e}")

    def look_at_screen(self, question: str = "What do you see on screen?") -> str:
        """
        Take a screenshot of the active window and analyze it with Gemini Flash.
        
        Args:
            question: What to look for or analyze on the screen.
        Returns:
            Description of what's on screen relevant to the question.
        """
        if not _SCREEN_AVAILABLE:
            return "Screen capture not available."
        
        img_bytes = _capture_active_window()
        if not img_bytes:
            return "Could not capture screen."

        if not self._client:
            return "Vision model not available (no API key)."

        try:
            from google.genai import types as genai_types
            img_b64 = base64.b64encode(img_bytes).decode()
            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    genai_types.Part(
                        inline_data=genai_types.Blob(
                            data=img_b64,
                            mime_type="image/jpeg"
                        )
                    ),
                    genai_types.Part(text=f"""
                        Analyze this screenshot carefully.
                        Question: {question}
                        
                        Describe what you see in detail, focusing on answering the question.
                        Include: what application is open, key UI elements visible,
                        any text content on screen, and any relevant details.
                        Be concise but thorough.
                    """)
                ]
            )
            return response.text or "No description available."
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return f"Vision analysis error: {e}"

    def find_element_coordinates(self, element_description: str) -> Optional[tuple]:
        """
        Find an on-screen element and return its (x, y) center coordinates.
        Uses Gemini vision to locate the element via bounding box.
        
        Args:
            element_description: Description of the UI element to find.
        Returns:
            (x, y) screen coordinates or None if not found.
        """
        if not _SCREEN_AVAILABLE or not self._client:
            return None

        img_bytes = _capture_active_window()
        if not img_bytes:
            return None

        try:
            from google.genai import types as genai_types
            import pygetwindow as gw
            import pyautogui

            win = gw.getActiveWindow()
            win_left = win.left if win else 0
            win_top = win.top if win else 0

            from PIL import Image
            import io
            img = Image.open(io.BytesIO(img_bytes))
            img_w, img_h = img.size

            img_b64 = base64.b64encode(img_bytes).decode()
            response = self._client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    genai_types.Part(
                        inline_data=genai_types.Blob(
                            data=img_b64,
                            mime_type="image/jpeg"
                        )
                    ),
                    genai_types.Part(text=f"""
                        Find this element: {element_description}
                        
                        Return ONLY a bounding box in format: [ymin, xmin, ymax, xmax]
                        Use normalized coordinates from 0 to 1000.
                        Example: [250, 100, 350, 400]
                        Return ONLY the array, no other text.
                    """)
                ]
            )
            text = response.text.strip()
            text = text.replace("[", "").replace("]", "")
            coords = [float(x.strip()) for x in text.split(",")]
            if len(coords) != 4:
                return None

            ymin, xmin, ymax, xmax = coords
            # Convert from 0-1000 normalized to screen pixels
            px_x = (xmin + (xmax - xmin) / 2) / 1000 * img_w + win_left
            px_y = (ymin + (ymax - ymin) / 2) / 1000 * img_h + win_top
            return (int(px_x), int(px_y))

        except Exception as e:
            logger.error(f"Element location failed: {e}")
            return None

    def get_active_window_title(self) -> str:
        """Return the title of the currently active window."""
        if not _SCREEN_AVAILABLE:
            return "unknown"
        try:
            return gw.getActiveWindowTitle() or "unknown"
        except Exception:
            return "unknown"

    def get_adk_tools(self) -> list:
        """Return ADK-compatible function declarations."""
        from google.genai import types as genai_types
        return [
            genai_types.FunctionDeclaration(
                name="look_at_screen",
                description=(
                    "Take a screenshot of the active window and analyze what's on screen. "
                    "Use this to understand the current state of the user's computer."
                ),
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "question": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="What to look for or analyze on the screen"
                        )
                    }
                )
            ),
            genai_types.FunctionDeclaration(
                name="find_and_click_element",
                description="Find a UI element on screen by description and click it.",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "element_description": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="Description of the UI element to find and click"
                        ),
                        "click_type": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="'left', 'double', or 'right'"
                        )
                    },
                    required=["element_description"]
                )
            ),
        ]

    def handle_tool_call(self, name: str, args: dict) -> str:
        """Dispatch a tool call."""
        if name == "look_at_screen":
            return self.look_at_screen(args.get("question", "What do you see?"))
        elif name == "find_and_click_element":
            desc = args.get("element_description", "")
            click_type = args.get("click_type", "left")
            coords = self.find_element_coordinates(desc)
            if coords:
                if _SCREEN_AVAILABLE:
                    pyautogui.moveTo(coords[0], coords[1], duration=0.2)
                    if click_type == "double":
                        pyautogui.doubleClick(*coords)
                    elif click_type == "right":
                        pyautogui.rightClick(*coords)
                    else:
                        pyautogui.click(*coords)
                    return f"Clicked {desc} at {coords}"
                return f"Found {desc} at {coords} but cannot click (pyautogui unavailable)"
            return f"Could not find element: {desc}"
        return f"Unknown screen tool: {name}"
