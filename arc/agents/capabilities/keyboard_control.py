"""
KeyboardControl capability — pyautogui + keyboard input emulation.
Ported from Jayu's keyboard.py with ADK tool wrapping.
"""

import logging
import time

logger = logging.getLogger("arc.capabilities.keyboard")

try:
    import pyautogui
    import keyboard as kb
    import pygetwindow as gw
    _KB_AVAILABLE = True
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
except ImportError:
    _KB_AVAILABLE = False
    logger.warning("pyautogui/keyboard not available — input control disabled")

IDE_NAMES = [
    "Visual Studio Code", "PyCharm", "Sublime", "Atom",
    "IntelliJ", "IDLE", "Jupyter", "Vim", "Emacs",
    "Brackets", "Eclipse", "NetBeans", "CLion", "Spyder",
]


def _fix_escape_sequences(text: str) -> str:
    """Fix double-escaped sequences from LLM JSON output."""
    return (
        text
        .replace("\\'", "'")
        .replace("\\\\", "\\")
        .replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
        .replace("\\b", "\b")
        .replace("\\f", "\f")
    )


def _is_ide_active() -> bool:
    if not _KB_AVAILABLE:
        return False
    try:
        title = gw.getActiveWindowTitle() or ""
        return any(ide.lower() in title.lower() for ide in IDE_NAMES)
    except Exception:
        return False


class KeyboardControlCapability:
    """
    Provides keyboard and mouse control tools for an AF agent.
    """

    def type_text(self, text: str) -> str:
        """
        Type out a string of text using the keyboard.
        
        Args:
            text: The text to type. Supports escape sequences like \\n for newlines.
        Returns:
            Confirmation message.
        """
        if not _KB_AVAILABLE:
            return "Keyboard control not available."
        text = _fix_escape_sequences(text)
        # Strip tabs if IDE auto-indent would conflict
        if _is_ide_active():
            text = text.replace("\t", "")
        try:
            kb.write(text, delay=0.008)
            return f"Typed {len(text)} characters."
        except Exception as e:
            return f"Type error: {e}"

    def press_hotkey(self, modifier: str, key: str) -> str:
        """
        Press a keyboard hotkey combination.
        
        Args:
            modifier: Modifier key ('ctrl', 'alt', 'shift', 'win').
            key: The key to press with the modifier (e.g. 'c', 'v', 's').
        Returns:
            Confirmation message.
        """
        if not _KB_AVAILABLE:
            return "Keyboard control not available."
        try:
            pyautogui.hotkey(modifier, key)
            return f"Pressed {modifier}+{key}"
        except Exception as e:
            return f"Hotkey error: {e}"

    def press_key(self, key: str, duration: float = 0.05) -> str:
        """
        Press and hold a key for a duration.
        
        Args:
            key: Key name (e.g. 'enter', 'escape', 'tab', 'space', 'up', 'down', 'a'-'z').
            duration: How long to hold the key in seconds.
        Returns:
            Confirmation message.
        """
        if not _KB_AVAILABLE:
            return "Keyboard control not available."
        try:
            pyautogui.keyDown(key)
            time.sleep(duration)
            pyautogui.keyUp(key)
            return f"Pressed {key} for {duration}s"
        except Exception as e:
            return f"Key press error: {e}"

    def mouse_click(self, x: float, y: float, click_type: str = "left") -> str:
        """
        Move the mouse to coordinates and click.
        
        Args:
            x: X screen coordinate.
            y: Y screen coordinate.
            click_type: 'left', 'right', or 'double'.
        Returns:
            Confirmation message.
        """
        if not _KB_AVAILABLE:
            return "Mouse control not available."
        try:
            pyautogui.moveTo(x, y, duration=0.15)
            if click_type == "double":
                pyautogui.doubleClick(x, y)
            elif click_type == "right":
                pyautogui.rightClick(x, y)
            else:
                pyautogui.click(x, y)
            return f"{click_type} click at ({x:.0f}, {y:.0f})"
        except Exception as e:
            return f"Mouse error: {e}"

    def scroll(self, direction: str = "down", clicks: int = 3) -> str:
        """
        Scroll the mouse wheel.
        
        Args:
            direction: 'up' or 'down'.
            clicks: Number of scroll clicks.
        Returns:
            Confirmation message.
        """
        if not _KB_AVAILABLE:
            return "Mouse control not available."
        amount = clicks if direction == "up" else -clicks
        pyautogui.scroll(amount)
        return f"Scrolled {direction} {clicks} clicks"

    def take_screenshot(self) -> str:
        """
        Take a screenshot and save it to the desktop.
        
        Returns:
            Path where screenshot was saved.
        """
        if not _KB_AVAILABLE:
            return "Screenshot not available."
        import os
        from PIL import ImageGrab
        path = os.path.expanduser("~/Desktop/arc_screenshot.png")
        img = ImageGrab.grab()
        img.save(path)
        return f"Screenshot saved to {path}"

    def get_adk_tools(self) -> list:
        """Return ADK-compatible function declarations."""
        from google.genai import types as genai_types

        return [
            genai_types.FunctionDeclaration(
                name="type_text",
                description="Type text using the keyboard in the currently focused application.",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "text": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="Text to type. Use \\n for newline, \\t for tab."
                        )
                    },
                    required=["text"]
                )
            ),
            genai_types.FunctionDeclaration(
                name="press_hotkey",
                description="Press a keyboard shortcut like Ctrl+C, Ctrl+S, Alt+Tab, etc.",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "modifier": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="Modifier key: 'ctrl', 'alt', 'shift', 'win'"
                        ),
                        "key": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="Key to press with modifier, e.g. 'c', 'v', 's', 'z'"
                        )
                    },
                    required=["modifier", "key"]
                )
            ),
            genai_types.FunctionDeclaration(
                name="press_key",
                description="Press a single keyboard key.",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "key": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="Key name: 'enter', 'escape', 'tab', 'space', 'up', 'down', etc."
                        ),
                        "duration": genai_types.Schema(
                            type=genai_types.Type.NUMBER,
                            description="Duration to hold key in seconds (default 0.05)"
                        )
                    },
                    required=["key"]
                )
            ),
            genai_types.FunctionDeclaration(
                name="mouse_click",
                description="Move mouse to screen coordinates and click.",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "x": genai_types.Schema(
                            type=genai_types.Type.NUMBER,
                            description="X screen coordinate"
                        ),
                        "y": genai_types.Schema(
                            type=genai_types.Type.NUMBER,
                            description="Y screen coordinate"
                        ),
                        "click_type": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="'left', 'right', or 'double'"
                        )
                    },
                    required=["x", "y"]
                )
            ),
            genai_types.FunctionDeclaration(
                name="scroll",
                description="Scroll the mouse wheel up or down.",
                parameters=genai_types.Schema(
                    type=genai_types.Type.OBJECT,
                    properties={
                        "direction": genai_types.Schema(
                            type=genai_types.Type.STRING,
                            description="'up' or 'down'"
                        ),
                        "clicks": genai_types.Schema(
                            type=genai_types.Type.INTEGER,
                            description="Number of scroll clicks"
                        )
                    }
                )
            ),
        ]

    def handle_tool_call(self, name: str, args: dict) -> str:
        """Dispatch a tool call."""
        dispatch = {
            "type_text":    lambda: self.type_text(args.get("text", "")),
            "press_hotkey": lambda: self.press_hotkey(args.get("modifier", "ctrl"), args.get("key", "")),
            "press_key":    lambda: self.press_key(args.get("key", ""), args.get("duration", 0.05)),
            "mouse_click":  lambda: self.mouse_click(args.get("x", 0), args.get("y", 0), args.get("click_type", "left")),
            "scroll":       lambda: self.scroll(args.get("direction", "down"), args.get("clicks", 3)),
            "take_screenshot": lambda: self.take_screenshot(),
        }
        fn = dispatch.get(name)
        return fn() if fn else f"Unknown keyboard tool: {name}"
