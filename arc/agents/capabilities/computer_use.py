"""
ComputerUseCapability — Screen control via Vertex AI.

Uses gemini-2.5-computer-use-preview-04-2025 on Vertex AI.
Falls back to VISION_MODEL if the Computer Use model is unavailable.

Authentication: Vertex AI ADC — no api_key.

Screenshot capture notes
────────────────────────
The ScreenOverlayWindow (arc/ui/screen_overlay.py) has WDA_EXCLUDEFROMCAPTURE
applied by Windows OS, so PIL's ImageGrab.grab() automatically omits those
overlay pixels. Gemini sees the clean desktop, not the floating tiles.
"""

import base64
import io
import json
import logging
import time
from typing import Optional

logger = logging.getLogger("arc.capabilities.computer_use")

# ── Optional deps with graceful fallback ──────────────────────────────────────
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE    = 0.08
    _PA_OK = True
except ImportError:
    _PA_OK = False
    logger.warning("pyautogui not available — mouse/click actions disabled")

try:
    import keyboard as _kb
    _KB_OK = True
except ImportError:
    _KB_OK = False
    logger.warning("keyboard not available — typing falls back to pyautogui")

try:
    import pygetwindow as gw
    from PIL import ImageGrab
    _SCR_OK = True
except ImportError:
    _SCR_OK = False
    logger.warning("pygetwindow/PIL not available — screen capture disabled")

from arc.core.models import COMPUTER_USE_MODEL, VISION_MODEL
from arc.core.vertex_config import make_standard_client


# ── Screen capture ─────────────────────────────────────────────────────────────

def _capture_jpeg(quality: int = 85) -> Optional[tuple[bytes, int, int]]:
    """
    Capture the active window as JPEG bytes.
    WDA_EXCLUDEFROMCAPTURE (set on ScreenOverlayWindow) ensures overlay tiles
    are invisible to this capture — Gemini sees the clean desktop.
    """
    if not _SCR_OK:
        return None
    try:
        win  = gw.getActiveWindow()
        bbox = (win.left, win.top, win.left + win.width, win.top + win.height) \
               if (win and win.width > 10) else None
        img  = ImageGrab.grab(bbox=bbox)
        w, h = img.size
        buf  = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=quality)
        return buf.getvalue(), w, h
    except Exception as e:
        logger.error(f"Capture failed: {e}")
        return None


def _norm_to_screen(nx: float, ny: float, img_w: int, img_h: int) -> tuple[int, int]:
    """Convert 0-1000 normalised coords → absolute screen pixels."""
    win = gw.getActiveWindow() if _SCR_OK else None
    ox  = win.left if win else 0
    oy  = win.top  if win else 0
    return int(nx / 1000 * img_w) + ox, int(ny / 1000 * img_h) + oy


# ── Capability class ───────────────────────────────────────────────────────────

class ComputerUseCapability:
    """
    Multi-step screen control backed by Vertex AI.

    Model: gemini-2.5-computer-use-preview-04-2025
    Auth:  ADC (no api_key)
    """

    _SYSTEM = """
You are a computer-use agent controlling a Windows desktop.
You receive a screenshot and a task description.
Output ONLY a JSON array of actions (no markdown fences, no prose).

Valid action objects:
  {"type":"click",   "x":0-1000, "y":0-1000, "button":"left|right|double"}
  {"type":"type",    "text":"..."}
  {"type":"key",     "key":"enter|escape|tab|backspace|delete|up|down|left|right|space|f1-f12|..."}
  {"type":"hotkey",  "modifiers":["ctrl"|"alt"|"shift"|"win"], "key":"..."}
  {"type":"scroll",  "direction":"up|down", "clicks":1-10}
  {"type":"screenshot"}          <- request fresh capture before next step
  {"type":"done",    "message":"summary of what was accomplished"}

Coordinates are 0-1000 (0,0 = top-left of the active window).
Include "done" as the final action when the task is complete.
If uncertain about an element's location, emit {"type":"screenshot"} first.
"""

    def __init__(self):
        """No api_key — uses Vertex AI ADC via make_standard_client()."""
        self._client = None
        try:
            self._client = make_standard_client()
        except Exception as e:
            logger.error(f"ComputerUse client init: {e}")

    # ── Action executor ───────────────────────────────────────────────────────

    def _exec(self, action: dict, img_w: int, img_h: int) -> str:
        t = action.get("type", "")

        if t == "click":
            if not _PA_OK:
                return "pyautogui not available"
            x, y   = _norm_to_screen(action["x"], action["y"], img_w, img_h)
            button = action.get("button", "left")
            pyautogui.moveTo(x, y, duration=0.15)
            {"left":   pyautogui.click,
             "right":  pyautogui.rightClick,
             "double": pyautogui.doubleClick}.get(button, pyautogui.click)(x, y)
            return f"Clicked ({x},{y}) [{button}]"

        elif t == "type":
            text = (action.get("text", "")
                    .replace("\\n", "\n").replace("\\t", "\t")
                    .replace("\\'", "'").replace("\\\\", "\\"))
            if _KB_OK:
                _kb.write(text, delay=0.008)
            elif _PA_OK:
                pyautogui.typewrite(text, interval=0.03)
            else:
                return "No typing backend available"
            return f"Typed {len(text)} chars"

        elif t == "key":
            if not _PA_OK:
                return "pyautogui not available"
            pyautogui.press(action.get("key", ""))
            return f"Pressed {action.get('key')}"

        elif t == "hotkey":
            if not _PA_OK:
                return "pyautogui not available"
            mods = action.get("modifiers", [])
            key  = action.get("key", "")
            pyautogui.hotkey(*mods, key)
            return f"Hotkey {'+'.join(mods)}+{key}"

        elif t == "scroll":
            if not _PA_OK:
                return "pyautogui not available"
            direction = action.get("direction", "down")
            clicks    = int(action.get("clicks", 3))
            pyautogui.scroll(clicks if direction == "up" else -clicks)
            return f"Scrolled {direction} ×{clicks}"

        elif t == "screenshot":
            return "__SCREENSHOT__"

        elif t == "done":
            return f"__DONE__:{action.get('message', 'Task complete')}"

        return f"Unknown action type: {t}"

    # ── Main entry point ──────────────────────────────────────────────────────

    def execute_task(self, task_description: str, max_steps: int = 8) -> str:
        """
        Execute a computer task autonomously via Vertex AI.
        Loops up to max_steps iterations, re-capturing the screen each time.
        """
        if not _SCR_OK:
            return "Screen capture not available."
        if not self._client:
            return "Computer Use model not available (Vertex AI not configured)."

        from google.genai import types as gt
        steps: list[str] = []
        step = 0

        while step < max_steps:
            capture = _capture_jpeg()
            if not capture:
                return "Screen capture failed."
            jpeg_bytes, img_w, img_h = capture
            b64 = base64.b64encode(jpeg_bytes).decode()

            win_title = (gw.getActiveWindowTitle() or "unknown") if _SCR_OK else "unknown"
            prompt = (
                f"Active window: {win_title}\n"
                f"Task: {task_description}\n"
                f"Steps done so far: {steps[-5:] or 'none'}\n\n"
                "Output the next action(s) as a JSON array."
            )

            try:
                resp = self._client.models.generate_content(
                    model=COMPUTER_USE_MODEL,
                    contents=[
                        gt.Part(inline_data=gt.Blob(data=b64, mime_type="image/jpeg")),
                        gt.Part(text=prompt),
                    ],
                    config=gt.GenerateContentConfig(
                        system_instruction=self._SYSTEM,
                        temperature=0.05,
                        max_output_tokens=800,
                    ),
                )
            except Exception as e:
                logger.error(f"Computer use call failed: {e}")
                # Fallback: try with vision model
                try:
                    resp = self._client.models.generate_content(
                        model=VISION_MODEL,
                        contents=[
                            gt.Part(inline_data=gt.Blob(data=b64, mime_type="image/jpeg")),
                            gt.Part(text=prompt),
                        ],
                        config=gt.GenerateContentConfig(
                            system_instruction=self._SYSTEM,
                            temperature=0.05,
                            max_output_tokens=800,
                        ),
                    )
                    logger.info("Fell back to VISION_MODEL for computer use")
                except Exception as e2:
                    return f"Computer use error: {e2}"

            raw = resp.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                raw = raw[4:] if raw.startswith("json") else raw
            raw = raw.strip()

            try:
                actions = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(f"Bad JSON from model: {raw[:200]}")
                break

            if not isinstance(actions, list):
                actions = [actions]

            need_screenshot = False
            for action in actions:
                result = self._exec(action, img_w, img_h)
                logger.info(f"CU action {action.get('type')}: {result}")

                if result == "__SCREENSHOT__":
                    steps.append("re-captured")
                    need_screenshot = True
                    break
                elif result.startswith("__DONE__:"):
                    msg = result[9:]
                    steps.append(f"✓ {msg}")
                    return f"✓ {msg}\n\nSteps: " + " → ".join(steps)
                else:
                    steps.append(result)
                    time.sleep(0.25)

            if not need_screenshot:
                step += 1

        return f"Task attempted ({step} steps): " + " → ".join(steps)

    # ── Single-click shortcut ─────────────────────────────────────────────────

    def click_element(self, description: str, click_type: str = "left") -> str:
        if not _SCR_OK or not self._client:
            return "Not available."
        capture = _capture_jpeg()
        if not capture:
            return "Screen capture failed."
        jpeg_bytes, img_w, img_h = capture
        b64 = base64.b64encode(jpeg_bytes).decode()

        from google.genai import types as gt
        try:
            resp = self._client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    gt.Part(inline_data=gt.Blob(data=b64, mime_type="image/jpeg")),
                    gt.Part(text=(
                        f"Find: {description}\n"
                        'Return ONLY JSON: {"x":0-1000,"y":0-1000} — centre of element.'
                    )),
                ],
                config=gt.GenerateContentConfig(temperature=0.0, max_output_tokens=60),
            )
            raw    = resp.text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            coords = json.loads(raw)
            nx, ny = float(coords["x"]), float(coords["y"])
            px, py = _norm_to_screen(nx, ny, img_w, img_h)
            if _PA_OK:
                pyautogui.moveTo(px, py, duration=0.18)
                {"left":   pyautogui.click,
                 "right":  pyautogui.rightClick,
                 "double": pyautogui.doubleClick}.get(click_type, pyautogui.click)(px, py)
            return f"Clicked '{description}' at ({px},{py})"
        except Exception as e:
            return f"Could not click '{description}': {e}"

    # ── ADK tool declarations ──────────────────────────────────────────────────

    def get_adk_tools(self) -> list:
        from google.genai import types as gt
        return [
            gt.FunctionDeclaration(
                name="computer_use",
                description=(
                    "Execute a multi-step computer task by controlling the screen "
                    "via Vertex AI. Use for: filling forms, navigating apps, "
                    "clicking through menus, composing documents, etc."
                ),
                parameters=gt.Schema(
                    type=gt.Type.OBJECT,
                    properties={
                        "task":      gt.Schema(type=gt.Type.STRING,
                                               description="What to do on screen"),
                        "max_steps": gt.Schema(type=gt.Type.INTEGER,
                                               description="Max steps (default 8, max 15)"),
                    },
                    required=["task"],
                ),
            ),
            gt.FunctionDeclaration(
                name="click_element",
                description="Find a UI element by description and click it (single click).",
                parameters=gt.Schema(
                    type=gt.Type.OBJECT,
                    properties={
                        "description": gt.Schema(type=gt.Type.STRING,
                                                  description="Description of element"),
                        "click_type":  gt.Schema(type=gt.Type.STRING,
                                                  description="'left','right','double'"),
                    },
                    required=["description"],
                ),
            ),
        ]

    def handle_tool_call(self, name: str, args: dict) -> str:
        if name == "computer_use":
            return self.execute_task(
                args.get("task", ""),
                max_steps=min(int(args.get("max_steps", 8)), 15),
            )
        elif name == "click_element":
            return self.click_element(
                args.get("description", ""),
                args.get("click_type", "left"),
            )
        return f"Unknown tool: {name}"