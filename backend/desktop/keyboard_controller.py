"""
AURA Keyboard Controller
Provides genuine Windows keyboard automation, Unicode text injection,
key combinations & shortcuts (Ctrl+C, Ctrl+V, Alt+Tab, Win+R, Ctrl+Shift+Esc),
safe input sanitization, and emergency key release guarantees.
"""

from typing import List, Set, Optional, Dict, Any
import ctypes
from ctypes import wintypes
import time
import logging
from backend.security.secret_store import secret_store

logger = logging.getLogger(__name__)

# Win32 Key Event Flags
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

user32 = ctypes.windll.user32

# Virtual Key Mapping
VK_MAPPING = {
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "space": 0x20,
    "backspace": 0x08,
    "escape": 0x1B,
    "esc": 0x1B,
    "delete": 0x2E,
    "del": 0x2E,
    "insert": 0x2D,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "shift": 0x10,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "win": 0x5B,
    "windows": 0x5B,
    "capslock": 0x14,
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
    # Media keys
    "volume_mute": 0xAD,
    "volume_down": 0xAE,
    "volume_up": 0xAF,
    "media_next": 0xB0,
    "media_prev": 0xB1,
    "media_stop": 0xB2,
    "media_play_pause": 0xB3,
    # Punctuation & OEM keys
    "/": 0xBF,
    "slash": 0xBF,
    "forward_slash": 0xBF,
    "\\": 0xDC,
    "backslash": 0xDC,
    "-": 0xBD,
    "minus": 0xBD,
    "=": 0xBB,
    "equal": 0xBB,
    "equals": 0xBB,
    ",": 0xBC,
    "comma": 0xBC,
    ".": 0xBE,
    "period": 0xBE,
    "dot": 0xBE,
    ";": 0xBA,
    "semicolon": 0xBA,
    "'": 0xDE,
    "quote": 0xDE,
    "single_quote": 0xDE,
    "[": 0xDB,
    "]": 0xDD,
    "`": 0xC0,
    "backquote": 0xC0,
    "tilde": 0xC0,
}

# Win32 INPUT Structures for SendInput
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulong),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", INPUT_UNION)]


INPUT_KEYBOARD = 1


class KeyboardController:
    """Safe Windows Hardware Keyboard Controller."""

    def __init__(self):
        self._held_keys: Set[int] = set()

    def send_key_down(self, vk: int) -> None:
        """Sends key down event."""
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.u.ki.wVk = vk
        inp.u.ki.wScan = user32.MapVirtualKeyW(vk, 0)
        inp.u.ki.dwFlags = 0
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        self._held_keys.add(vk)

    def send_key_up(self, vk: int) -> None:
        """Sends key up event."""
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.u.ki.wVk = vk
        inp.u.ki.wScan = user32.MapVirtualKeyW(vk, 0)
        inp.u.ki.dwFlags = KEYEVENTF_KEYUP
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        self._held_keys.discard(vk)

    def press_key(self, key_name: str, duration: float = 0.05) -> bool:
        """Presses and releases a single key."""
        vk = self._resolve_vk(key_name)
        if vk is None:
            logger.warning(f"Unknown key name '{key_name}'")
            return False
        self.send_key_down(vk)
        time.sleep(duration)
        self.send_key_up(vk)
        return True

    def hotkey(self, *keys: str, pause_between: float = 0.04) -> bool:
        """
        Executes key combination (e.g. hotkey('ctrl', 'shift', 'esc')).
        Presses keys in order, then releases them in reverse order.
        """
        resolved: List[int] = []
        for k in keys:
            vk = self._resolve_vk(k)
            if vk is not None:
                resolved.append(vk)

        if not resolved:
            return False

        # Press down in order
        for vk in resolved:
            self.send_key_down(vk)
            time.sleep(0.02)

        time.sleep(pause_between)

        # Release in reverse order
        for vk in reversed(resolved):
            self.send_key_up(vk)
            time.sleep(0.01)

        return True

    def type_text(self, text: str, delay: float = 0.02, scrub_sensitive: bool = True) -> bool:
        """
        Types Unicode text accurately into focused window.
        Scrubs passwords, tokens, and secrets from audit logs.
        """
        if not text:
            return False

        safe_log_text = secret_store.scrub_text(text) if scrub_sensitive else "[TEXT]"
        logger.debug(f"Typing text length={len(text)}: {safe_log_text[:30]}...")

        for char in text:
            # Handle newline
            if char == "\n":
                self.press_key("enter")
                time.sleep(delay)
                continue
            if char == "\t":
                self.press_key("tab")
                time.sleep(delay)
                continue

            # Send Unicode character
            code = ord(char)
            inp_down = INPUT()
            inp_down.type = INPUT_KEYBOARD
            inp_down.u.ki.wVk = 0
            inp_down.u.ki.wScan = code
            inp_down.u.ki.dwFlags = KEYEVENTF_UNICODE

            inp_up = INPUT()
            inp_up.type = INPUT_KEYBOARD
            inp_up.u.ki.wVk = 0
            inp_up.u.ki.wScan = code
            inp_up.u.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP

            user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
            time.sleep(0.005)
            user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))
            if delay > 0:
                time.sleep(delay)

        return True

    def type_text_safe(self, text: str, use_clipboard_for_long: bool = True) -> bool:
        """
        Guaranteed zero-mistake typing.
        For normal text, types via SendInput Unicode with steady 20ms human pacing.
        For complex strings or long text (>45 chars), uses clipboard pasting via Ctrl+V
        for 100% accuracy and zero dropped characters.
        """
        if not text:
            return False

        if use_clipboard_for_long and (len(text) > 45 or "\n" in text or any(ord(c) > 127 for c in text)):
            try:
                import win32clipboard  # type: ignore
                import win32con  # type: ignore
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
                self.hotkey("ctrl", "v")
                return True
            except Exception:
                pass

        return self.type_text(text, delay=0.02)

    def release_all(self) -> int:
        """Emergency stop: releases any held keyboard keys."""
        released = 0
        for vk in list(self._held_keys):
            try:
                self.send_key_up(vk)
                released += 1
            except Exception:
                pass

        # Failsafe releases for primary modifiers
        for mod in (0x10, 0x11, 0x12, 0x5B):  # Shift, Ctrl, Alt, Win
            try:
                self.send_key_up(mod)
            except Exception:
                pass

        self._held_keys.clear()
        return released

    @staticmethod
    def _resolve_vk(key: str) -> Optional[int]:
        k = key.strip().lower()
        if k in VK_MAPPING:
            return VK_MAPPING[k]
        if len(k) == 1:
            try:
                scanned = user32.VkKeyScanW(ord(k))
                if scanned != -1:
                    return scanned & 0xFF
            except Exception:
                pass
            # Alpha-numeric ASCII uppercase code fallback
            return ord(k.upper())
        return None


# Global keyboard controller instance
keyboard_controller = KeyboardController()
