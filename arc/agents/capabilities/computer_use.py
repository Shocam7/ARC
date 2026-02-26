"""
ComputerUseCapability — Screen control via Gemini 2.5 Computer Use.

Uses `gemini-2.5-computer-use-preview-10-2025`, a model trained specifically
to receive a screenshot and return structured computer actions (click, type,
scroll, drag, hotkey…).

This is a significant upgrade over the raw pyautogui approach:
- The model understands UI context, not just pixel coordinates
- It can chain multiple actions for complex tasks
- It handles ambiguous element descriptions gracefully
- It can be told "fill this form" and figures out each field itself
"""

import base64
import io
import logging
import time
from typing import Optional

logger = logging.getLogger("arc.capabilities.computer_use")

try:
    import pyautogui
    import pygetwindow as gw
    from PIL import ImageGrab, Image
    _SCREEN_AVAILABLE = True
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.08
except ImportError:
    _SCREEN_AVAILABLE = False
    logger.warning("pyautogui/PIL not available — computer use disabled")

from arc.core.models import COMPUTER_USE_MODEL, VISION_MODEL


def _capture_window_jpeg(quality: int = 85) -> Optional[tuple[bytes, int, int]]:
    """
    Capture the active window as JPEG bytes.
    Returns (jpeg_bytes, width, height) or None on failure.
    """
    if not _SCREEN_AVAILABLE:
        return None
    try:
        win = gw.getActiveWindow()
        if win and win.width > 0:
            bbox = (win.left, win.top, win.left + win.width, win.top + win.height)
        else:
            bbox = None
        img = ImageGrab.grab(bbox=bbox)
        w, h = img.size
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=quality)
        return buf.getvalue(), w, h
    except Exception as e:
        logger.error(f"Capture failed: {e}")
        return None


def _norm_to_screen(nx: float, ny: float, img_w: int, img_h: int) -> tuple[int, int]:
    """Convert 0-1000 normalised coordinates to actual screen pixels."""
    win = gw.getActiveWindow() if _SCREEN_AVAILABLE else None
    ox = win.left if win else 0
    oy = win.top  if win else 0
    px = int(nx / 1000 * img_w) + ox
    py = int(ny / 1000 * img_h) + oy
    return px, py


class ComputerUseCapability:
    """
    Provides high-level computer control tools backed by
    gemini-2.5-computer-use-preview-10-2025.

    The model receives the current screenshot + a task description,
    then returns one or more actions to execute.

    For each action type the model can return:
        click       → {"type": "click",    "x": 0-1000, "y": 0-1000, "button": "left|right|double"}
        type        → {"type": "type",     "text": "..."}
        key         → {"type": "key",      "key": "enter|escape|tab|..."}
        hotkey      → {"type": "hotkey",   "modifiers": ["ctrl"], "key": "s"}
        scroll      → {"type": "scroll",   "direction": "up|down", "clicks": 3}
        screenshot  → {"type": "screenshot"}   (re-capture and return context)
        done        → {"type": "done",     "message": "..."}
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None
        if api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.error(f"ComputerUse client init failed: {e}")

    # ── Core action executor ──────────────────────────────────────────────────

    def _execute_action(self, action: dict, img_w: int, img_h: int) -> str:
        """Execute a single action dict returned by the model."""
        atype = action.get("type", "")

        if atype == "click":
            x, y = _norm_to_screen(action["x"], action["y"], img_w, img_h)
            button = action.get("button", "left")
            pyautogui.moveTo(x, y, duration=0.15)
            if button == "double":
                pyautogui.doubleClick(x, y)
            elif button == "right":
                pyautogui.rightClick(x, y)
            else:
                pyautogui.click(x, y)
            return f"Clicked ({x},{y}) [{button}]"

        elif atype == "type":
            text = action.get("text", "")
            # Fix LLM escape sequences
            text = (text.replace("\\n", "\n").replace("\\t", "\t")
                        .replace("\\'", "'").replace("\\\\", "\\"))
            import keyboard as kb
            kb.write(text, delay=0.008)
            return f"Typed {len(text)} chars"

        elif atype == "key":
            key = action.get("key", "")
            pyautogui.press(key)
            return f"Pressed {key}"

        elif atype == "hotkey":
            mods = action.get("modifiers", [])
            key  = action.get("key", "")
            pyautogui.hotkey(*mods, key)
            return f"Hotkey {'+'.join(mods)}+{key}"

        elif atype == "scroll":
            direction = action.get("direction", "down")
            clicks    = int(action.get("clicks", 3))
            amount = clicks if direction == "up" else -clicks
            pyautogui.scroll(amount)
            return f"Scrolled {direction} {clicks}"

        elif atype == "screenshot":
            return "Screenshot requested (will re-capture)"

        elif atype == "done":
            return f"Done: {action.get('message', 'Task complete')}"

        else:
            return f"Unknown action type: {atype}"

    # ── Main computer-use call ─────────────────────────────────────────────────

    def execute_task(self, task_description: str, max_steps: int = 8) -> str:
        """
        Execute a computer task using the dedicated Computer Use model.

        The model sees the screen, plans actions, and we execute them one by one.
        Loops up to max_steps times or until the model signals "done".

        Args:
            task_description: Natural language description of what to do.
            max_steps: Safety limit on action steps (default 8).
        Returns:
            Summary of what was accomplished.
        """
        if not _SCREEN_AVAILABLE:
            return "Screen control not available."
        if not self._client:
            return "Computer Use model not available (no API key)."

        import json
        from google.genai import types as gt

        SYSTEM = """
You are a computer-use agent controlling a Windows desktop.
You receive a screenshot and a task. You output a JSON array of actions to perform.

Each action must be one of:
  {"type":"click",    "x":0-1000, "y":0-1000, "button":"left|right|double"}
  {"type":"type",     "text":"string to type"}
  {"type":"key",      "key":"enter|escape|tab|backspace|delete|up|down|left|right|space|..."}
  {"type":"hotkey",   "modifiers":["ctrl"|"alt"|"shift"|"win"], "key":"letter or key"}
  {"type":"scroll",   "direction":"up|down", "clicks":1-10}
  {"type":"screenshot"}    <- request an updated screenshot before continuing
  {"type":"done",     "message":"summary of what was accomplished"}

Coordinates are normalised 0-1000 (0,0 = top-left of the active window).
Output ONLY a JSON array. No explanation text. No markdown fences.
Stop as soon as the task is accomplished — include a "done" action last.
Be precise. If unsure where an element is, use type:screenshot to look again.
"""

        steps_taken = []
        step = 0

        while step < max_steps:
            capture = _capture_window_jpeg()
            if not capture:
                return "Screen capture failed."
            jpeg_bytes, img_w, img_h = capture
            img_b64 = base64.b64encode(jpeg_bytes).decode()

            win_title = gw.getActiveWindowTitle() or "unknown"
            prompt = (
                f"Active window: {win_title}\n"
                f"Task: {task_description}\n"
                f"Steps already done: {steps_taken[-6:] if steps_taken else 'none'}\n\n"
                "What actions should be taken next? Output JSON array only."
            )

            try:
                response = self._client.models.generate_content(
                    model=COMPUTER_USE_MODEL,
                    contents=[
                        gt.Part(
                            inline_data=gt.Blob(data=img_b64, mime_type="image/jpeg")
                        ),
                        gt.Part(text=prompt),
                    ],
                    config=gt.GenerateContentConfig(
                        system_instruction=SYSTEM,
                        temperature=0.05,
                        max_output_tokens=800,
                    )
                )
            except Exception as e:
                logger.error(f"Computer use model call failed: {e}")
                return f"Computer use error: {e}"

            raw = response.text.strip()
            # Strip markdown
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            try:
                actions = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(f"Bad JSON from computer use model: {raw[:200]}")
                break

            if not isinstance(actions, list):
                actions = [actions]

            for action in actions:
                atype = action.get("type", "")
                logger.info(f"ComputerUse action: {action}")

                if atype == "screenshot":
                    # Re-capture before next iteration
                    steps_taken.append("Re-captured screenshot")
                    break
                elif atype == "done":
                    msg = action.get("message", "Task complete")
                    steps_taken.append(f"DONE: {msg}")
                    return f"✓ {msg}\n\nSteps: " + " → ".join(steps_taken)
                else:
                    result = self._execute_action(action, img_w, img_h)
                    steps_taken.append(result)
                    time.sleep(0.3)  # allow UI to update between actions

            step += 1

        summary = " → ".join(steps_taken) if steps_taken else "No actions taken"
        return f"Task attempted ({step} steps): {summary}"

    # ── Simpler single-action: click element by description ────────────────────

    def click_element(self, description: str, click_type: str = "left") -> str:
        """
        Find a UI element by description and click it.
        Uses Vision model for locating, then executes the click.

        Args:
            description: Natural language description of the element.
            click_type:  "left", "right", or "double".
        Returns:
            Result string.
        """
        if not _SCREEN_AVAILABLE or not self._client:
            return "Not available."

        capture = _capture_window_jpeg()
        if not capture:
            return "Screen capture failed."
        jpeg_bytes, img_w, img_h = capture
        img_b64 = base64.b64encode(jpeg_bytes).decode()

        from google.genai import types as gt
        prompt = (
            f"Find this element: {description}\n"
            "Return ONLY a JSON object: "
            '{"x": 0-1000, "y": 0-1000}\n'
            "Use the center of the element. No other text."
        )
        try:
            response = self._client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    gt.Part(inline_data=gt.Blob(data=img_b64, mime_type="image/jpeg")),
                    gt.Part(text=prompt),
                ],
                config=gt.GenerateContentConfig(temperature=0.0, max_output_tokens=60)
            )
            import json
            raw = response.text.strip().strip("```json").strip("```").strip()
            coords = json.loads(raw)
            nx, ny = float(coords["x"]), float(coords["y"])
            px, py = _norm_to_screen(nx, ny, img_w, img_h)
            pyautogui.moveTo(px, py, duration=0.18)
            if click_type == "double":
                pyautogui.doubleClick(px, py)
            elif click_type == "right":
                pyautogui.rightClick(px, py)
            else:
                pyautogui.click(px, py)
            return f"Clicked '{description}' at screen ({px},{py})"
        except Exception as e:
            logger.error(f"click_element failed: {e}")
            return f"Could not click '{description}': {e}"

    # ── ADK tool declarations ─────────────────────────────────────────────────

    def get_adk_tools(self) -> list:
        from google.genai import types as gt
        return [
            gt.FunctionDeclaration(
                name="computer_use",
                description=(
                    "Execute a computer task by controlling the screen. "
                    "Use this for complex multi-step UI tasks: filling forms, "
                    "navigating apps, clicking through menus, composing emails, etc. "
                    "The model will see the screen and perform the actions itself."
                ),
                parameters=gt.Schema(
                    type=gt.Type.OBJECT,
                    properties={
                        "task": gt.Schema(
                            type=gt.Type.STRING,
                            description="Clear description of what to do on screen"
                        ),
                        "max_steps": gt.Schema(
                            type=gt.Type.INTEGER,
                            description="Max action steps (default 8, max 15)"
                        ),
                    },
                    required=["task"]
                )
            ),
            gt.FunctionDeclaration(
                name="click_element",
                description=(
                    "Find a specific UI element on screen by description and click it. "
                    "Use for simple single-click tasks."
                ),
                parameters=gt.Schema(
                    type=gt.Type.OBJECT,
                    properties={
                        "description": gt.Schema(
                            type=gt.Type.STRING,
                            description="Description of the UI element to click"
                        ),
                        "click_type": gt.Schema(
                            type=gt.Type.STRING,
                            description="'left', 'right', or 'double'"
                        ),
                    },
                    required=["description"]
                )
            ),
        ]

    def handle_tool_call(self, name: str, args: dict) -> str:
        if name == "computer_use":
            max_steps = min(int(args.get("max_steps", 8)), 15)
            return self.execute_task(args.get("task", ""), max_steps=max_steps)
        elif name == "click_element":
            return self.click_element(
                args.get("description", ""),
                args.get("click_type", "left")
            )
        return f"Unknown computer use tool: {name}"
