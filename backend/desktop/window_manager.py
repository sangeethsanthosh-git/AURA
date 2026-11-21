"""
AURA Window Manager
Provides reliable Windows window discovery, focus management, state changes
(minimize, maximize, restore, close), thread input attachment for focus-stealing,
and multi-process identification.
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import ctypes
from ctypes import wintypes
import time
import os
import psutil
import logging

logger = logging.getLogger(__name__)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_MAXIMIZE = 3
SW_SHOW = 5
SW_MINIMIZE = 6
SW_RESTORE = 9
WM_CLOSE = 0x0010


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


user32.OpenInputDesktop.restype = wintypes.HANDLE
user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.OpenDesktopW.restype = wintypes.HANDLE
user32.OpenDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.SetThreadDesktop.argtypes = [wintypes.HANDLE]
user32.SetThreadDesktop.restype = wintypes.BOOL

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumDesktopWindows.argtypes = [wintypes.HANDLE, WNDENUMPROC, wintypes.LPARAM]
user32.EnumDesktopWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wintypes.BOOL

_DEFAULT_DESKTOP_HANDLE = None


def ensure_interactive_desktop():
    """Ensure the calling thread is attached to the user's interactive desktop."""
    global _DEFAULT_DESKTOP_HANDLE
    try:
        hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
        if not hdesk:
            hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hdesk:
            _DEFAULT_DESKTOP_HANDLE = hdesk
            user32.SetThreadDesktop(hdesk)
            return hdesk
    except Exception as e:
        logger.debug(f"Could not bind thread to interactive Default desktop: {e}")
    return None


class WindowManager:
    """Manages active Windows windows and focus."""

    @staticmethod
    def get_foreground_window() -> Dict[str, Any]:
        """Returns details of the currently focused active window."""
        ensure_interactive_desktop()
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return {"hwnd": 0, "title": "", "process_name": "", "pid": 0, "rect": {}}

        title = WindowManager.get_window_title(hwnd)
        pid = WindowManager.get_window_pid(hwnd)
        process_name = ""
        if pid:
            try:
                process_name = psutil.Process(pid).name()
            except Exception:
                pass

        rect = WindowManager.get_window_rect(hwnd)
        return {
            "hwnd": hwnd,
            "title": title,
            "process_name": process_name,
            "pid": pid,
            "rect": rect,
        }

    @staticmethod
    def get_window_title(hwnd: int) -> str:
        """Retrieves title of a window."""
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        return ""

    @staticmethod
    def get_window_pid(hwnd: int) -> int:
        """Retrieves process ID owning the window."""
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value)

    @staticmethod
    def get_window_rect(hwnd: int) -> Dict[str, int]:
        """Retrieves bounding rectangle (x, y, width, height) of a window."""
        r = RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return {
                "x": r.left,
                "y": r.top,
                "width": max(0, r.right - r.left),
                "height": max(0, r.bottom - r.top),
            }
        return {"x": 0, "y": 0, "width": 0, "height": 0}

    @classmethod
    def list_windows(cls, visible_only: bool = True) -> List[Dict[str, Any]]:
        """Lists all open windows with non-empty titles."""
        ensure_interactive_desktop()
        windows: List[Dict[str, Any]] = []

        def _enum_cb(hwnd, lparam):
            if visible_only and not user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
                return 1

            title = cls.get_window_title(hwnd).strip()
            pid = cls.get_window_pid(hwnd)
            proc_name = ""
            if pid:
                try:
                    proc_name = psutil.Process(pid).name()
                except Exception:
                    pass

            # Ignore internal system windows, background host workers, and message-only surfaces
            skip_terms = (
                "program manager",
                "windows shell experience host",
                "default ime",
                "msctfime ui",
                "olemainthreadwndname",
                "gdi+ window",
                "cua.agentcursoroverlay",
                "systemmsg_keystone",
                "atkosd2",
            )
            if not title or any(skip in title.lower() for skip in skip_terms):
                return 1

            rect = cls.get_window_rect(hwnd)
            # A real interactive user window must have substantial width and height
            if rect["width"] < 150 or rect["height"] < 100:
                return 1

            windows.append({
                "hwnd": hwnd,
                "title": title,
                "process_name": proc_name,
                "pid": pid,
                "rect": rect,
                "is_minimized": bool(user32.IsIconic(hwnd)),
                "is_maximized": bool(user32.IsZoomed(hwnd)),
            })
            return 1

        hdesk = ensure_interactive_desktop()
        cb = WNDENUMPROC(_enum_cb)
        if hdesk:
            user32.EnumDesktopWindows(hdesk, cb, 0)
        else:
            user32.EnumWindows(cb, 0)
        return windows

    @classmethod
    def find_window(cls, query: str) -> Optional[Dict[str, Any]]:
        """Finds the most relevant open window matching query (by title or process name)."""
        q = query.lower().strip()
        all_wins = cls.list_windows()

        # Score and rank candidates
        candidates = []
        for win in all_wins:
            t = win["title"].lower()
            p = win["process_name"].lower()
            w = win.get("rect", {}).get("width", 0)
            h = win.get("rect", {}).get("height", 0)

            score = 0
            if q == t:
                score += 2000
            elif q in t:
                score += 1000
            elif q in p:
                score += 500
            else:
                tokens = [word for word in q.split() if len(word) > 2]
                if any(tok in t for tok in tokens):
                    score += 400
                elif any(tok in p for tok in tokens):
                    score += 200

            if score > 0:
                # Add window area bonus so larger main windows are prioritized over tooltips
                score += min(w * h // 1000, 500)
                candidates.append((score, win))

        if candidates:
            candidates.sort(key=lambda c: c[0], reverse=True)
            return candidates[0][1]

        return None

    @classmethod
    def focus_window(cls, hwnd_or_query: Union[int, str]) -> bool:
        """
        Forces target window to the foreground, bypassing Windows focus-stealing blocks.
        """
        hwnd = 0
        if isinstance(hwnd_or_query, int):
            hwnd = hwnd_or_query
        else:
            found = cls.find_window(hwnd_or_query)
            if found:
                hwnd = found["hwnd"]

        if not hwnd or not user32.IsWindow(hwnd):
            logger.warning(f"Window '{hwnd_or_query}' not found or invalid hwnd.")
            return False

        try:
            user32.AllowSetForegroundWindow(-1)
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)
            else:
                user32.ShowWindow(hwnd, SW_SHOW)

            # Thread Input attachment trick for reliable foreground focus bypassing Windows lock
            cur_thread = kernel32.GetCurrentThreadId()
            fore_hwnd = user32.GetForegroundWindow()
            fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None) if fore_hwnd else 0
            target_thread = user32.GetWindowThreadProcessId(hwnd, None) if hwnd else 0

            attached_fore = False
            attached_target = False
            if fore_thread and cur_thread != fore_thread:
                attached_fore = bool(user32.AttachThreadInput(cur_thread, fore_thread, True))
            if target_thread and cur_thread != target_thread:
                attached_target = bool(user32.AttachThreadInput(cur_thread, target_thread, True))

            # Pulse Alt key to bypass Windows LockSetForegroundWindow restriction
            try:
                user32.keybd_event(0x12, 0, 0, 0)  # VK_MENU down
                user32.keybd_event(0x12, 0, 2, 0)  # VK_MENU up
            except Exception:
                pass

            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            user32.SetActiveWindow(hwnd)

            if attached_fore:
                user32.AttachThreadInput(cur_thread, fore_thread, False)
            if attached_target:
                user32.AttachThreadInput(cur_thread, target_thread, False)

            time.sleep(0.08)
            return True
        except Exception as e:
            logger.error(f"Error focusing window {hwnd}: {e}")
            return False

    @classmethod
    def maximize_window(cls, hwnd_or_query: Union[int, str]) -> bool:
        """Maximizes window."""
        found = cls.find_window(str(hwnd_or_query)) if isinstance(hwnd_or_query, str) else {"hwnd": hwnd_or_query}
        if not found or not found.get("hwnd"):
            return False
        return bool(user32.ShowWindowAsync(found["hwnd"], SW_MAXIMIZE))

    @classmethod
    def minimize_window(cls, hwnd_or_query: Union[int, str]) -> bool:
        """Minimizes window."""
        found = cls.find_window(str(hwnd_or_query)) if isinstance(hwnd_or_query, str) else {"hwnd": hwnd_or_query}
        if not found or not found.get("hwnd"):
            return False
        return bool(user32.ShowWindowAsync(found["hwnd"], SW_MINIMIZE))

    @classmethod
    def restore_window(cls, hwnd_or_query: Union[int, str]) -> bool:
        """Restores window to normal dimensions."""
        found = cls.find_window(str(hwnd_or_query)) if isinstance(hwnd_or_query, str) else {"hwnd": hwnd_or_query}
        if not found or not found.get("hwnd"):
            return False
        return bool(user32.ShowWindowAsync(found["hwnd"], SW_RESTORE))

    @classmethod
    def close_window(cls, hwnd_or_query: Union[int, str]) -> bool:
        """Gracefully closes window via WM_CLOSE."""
        found = cls.find_window(str(hwnd_or_query)) if isinstance(hwnd_or_query, str) else {"hwnd": hwnd_or_query}
        if not found or not found.get("hwnd"):
            return False
        return bool(user32.PostMessageW(found["hwnd"], WM_CLOSE, 0, 0))


# Global window manager instance
window_manager = WindowManager()
