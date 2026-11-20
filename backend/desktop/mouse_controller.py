"""
AURA Mouse Controller
Provides genuine Windows hardware mouse control, multi-monitor geometry detection,
DPI-aware coordinate mapping, human-like smooth easing trajectories, click actions,
drag-and-drop, scroll wheel manipulation, and emergency release guarantees.
"""

from typing import Tuple, List, Dict, Any, Optional
import ctypes
from ctypes import wintypes
import time
import math
import logging

logger = logging.getLogger(__name__)

# Win32 Mouse Event Flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
MOUSEEVENTF_ABSOLUTE = 0x8000

# System Metrics
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_CMONITORS = 80

user32 = ctypes.windll.user32


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class MONITORINFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


class MouseController:
    """Zero-Trust DPI-Aware Windows Mouse Controller with Human Trajectory Easing."""

    def __init__(self):
        self._set_dpi_awareness()
        self._held_buttons = set()

    @staticmethod
    def _set_dpi_awareness() -> None:
        """Enforces Per-Monitor V2 DPI awareness for 1:1 physical pixel accuracy."""
        try:
            # PROCESS_PER_MONITOR_DPI_AWARE_V2 = 2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass

    def get_position(self) -> Tuple[int, int]:
        """Returns the current mouse pointer coordinate (x, y)."""
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return int(pt.x), int(pt.y)

    def get_screen_resolution(self) -> Tuple[int, int]:
        """Returns primary monitor resolution (width, height)."""
        w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
        h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        return int(w), int(h)

    def get_virtual_desktop_bounds(self) -> Dict[str, int]:
        """Returns bounds of all connected monitors combined."""
        x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        return {"x": x, "y": y, "width": w, "height": h}

    def get_monitors(self) -> List[Dict[str, Any]]:
        """Enumerates all active physical and virtual displays."""
        monitors: List[Dict[str, Any]] = []

        def _enum_cb(hMonitor, hdcMonitor, lprcMonitor, dwData):
            info = MONITORINFOEX()
            info.cbSize = ctypes.sizeof(MONITORINFOEX)
            if user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
                r = info.rcMonitor
                w_rect = info.rcWork
                is_primary = bool(info.dwFlags & 1)
                monitors.append({
                    "name": info.szDevice,
                    "is_primary": is_primary,
                    "x": r.left,
                    "y": r.top,
                    "width": r.right - r.left,
                    "height": r.bottom - r.top,
                    "work_area": {
                        "x": w_rect.left,
                        "y": w_rect.top,
                        "width": w_rect.right - w_rect.left,
                        "height": w_rect.bottom - w_rect.top,
                    },
                })
            return 1

        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HMONITOR,
            wintypes.HDC,
            ctypes.POINTER(RECT),
            wintypes.LPARAM,
        )
        user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_enum_cb), 0)
        return monitors

    def move_to(
        self,
        target_x: int,
        target_y: int,
        smooth: bool = True,
        duration: float = 0.35,
        steps: int = 30,
    ) -> bool:
        """
        Moves mouse pointer to (target_x, target_y).
        If smooth is True, executes human-like cubic bezier trajectory easing.
        """
        start_x, start_y = self.get_position()
        if start_x == target_x and start_y == target_y:
            return True

        if not smooth or duration <= 0:
            user32.SetCursorPos(int(target_x), int(target_y))
            return True

        # Cubic Ease-in-out interpolation
        delay_per_step = max(0.005, duration / max(5, steps))
        for step in range(1, steps + 1):
            t = step / steps
            # Ease-in-out formula: 3t^2 - 2t^3
            eased_t = t * t * (3.0 - 2.0 * t)
            cur_x = int(start_x + (target_x - start_x) * eased_t)
            cur_y = int(start_y + (target_y - start_y) * eased_t)
            user32.SetCursorPos(cur_x, cur_y)
            time.sleep(delay_per_step)

        user32.SetCursorPos(int(target_x), int(target_y))
        return True

    def click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.1,
    ) -> bool:
        """Performs single or multiple clicks at current or specified coordinate."""
        if x is not None and y is not None:
            self.move_to(x, y, smooth=True)

        down_flag, up_flag = self._get_button_flags(button)

        for i in range(clicks):
            user32.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(0.025)
            user32.mouse_event(up_flag, 0, 0, 0, 0)
            if i < clicks - 1 and interval > 0:
                time.sleep(interval)
        return True

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Performs double left click."""
        return self.click(x=x, y=y, button="left", clicks=2, interval=0.08)

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Performs right click."""
        return self.click(x=x, y=y, button="right", clicks=1)

    def press_mouse(self, button: str = "left") -> bool:
        """Holds mouse button down."""
        down_flag, _ = self._get_button_flags(button)
        user32.mouse_event(down_flag, 0, 0, 0, 0)
        self._held_buttons.add(button.lower())
        return True

    def release_mouse(self, button: str = "left") -> bool:
        """Releases held mouse button."""
        _, up_flag = self._get_button_flags(button)
        user32.mouse_event(up_flag, 0, 0, 0, 0)
        self._held_buttons.discard(button.lower())
        return True

    def drag_and_drop(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
    ) -> bool:
        """Performs genuine drag-and-drop between two coordinates."""
        self.move_to(start_x, start_y, smooth=True)
        time.sleep(0.05)
        self.press_mouse("left")
        time.sleep(0.08)
        self.move_to(end_x, end_y, smooth=True, duration=duration)
        time.sleep(0.08)
        self.release_mouse("left")
        time.sleep(0.05)
        return True

    def scroll(self, clicks: int, horizontal: bool = False) -> bool:
        """
        Scrolls mouse wheel.
        clicks: positive scrolls UP/RIGHT, negative scrolls DOWN/LEFT.
        """
        delta = int(clicks * 120)
        flag = MOUSEEVENTF_HWHEEL if horizontal else MOUSEEVENTF_WHEEL
        user32.mouse_event(flag, 0, 0, delta, 0)
        return True

    def release_all(self) -> int:
        """Emergency stop: releases any held mouse buttons."""
        released = 0
        for btn in list(self._held_buttons):
            self.release_mouse(btn)
            released += 1
        # Failsafe unconditional release
        user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        user32.mouse_event(MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)
        self._held_buttons.clear()
        return released

    @staticmethod
    def _get_button_flags(button: str) -> Tuple[int, int]:
        b = button.lower()
        if b == "right":
            return MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
        elif b == "middle":
            return MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
        return MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP


# Global mouse controller instance
mouse_controller = MouseController()
