"""
AURA Phase 7: Windows Desktop & System Control Service.
Provides native OS controls for audio volume, app launching, hardware diagnostics,
media playback, clipboard inspection, and web automation without third-party bloat.
"""

from typing import Optional, Dict, Any
import ctypes
from ctypes import wintypes
import logging
import os
import re
import subprocess
import urllib.parse
import webbrowser
import psutil

from backend.services.vision_service import VisionService
from backend.services.rag_service import RAGService
from backend.services.reminder_service import ReminderService
from backend.security.sandbox import AuraSandboxProtocol

logger = logging.getLogger(__name__)

# Windows Virtual-Key Codes for User32 keybd_event
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Setup Windows Clipboard API signatures
CF_UNICODETEXT = 13
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL


SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_MAXIMIZE = 3
SW_SHOWNOACTIVATE = 4
SW_SHOW = 5
SW_MINIMIZE = 6
SW_RESTORE = 9

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


def force_foreground_window(hwnd: int) -> bool:
    """Force an existing window to the foreground, bypassing Windows focus restrictions."""
    try:
        ensure_interactive_desktop()
        user32.AllowSetForegroundWindow(-1)
        if user32.IsIconic(hwnd):
            user32.ShowWindowAsync(hwnd, SW_RESTORE)
        else:
            user32.ShowWindow(hwnd, SW_SHOW)
            user32.ShowWindowAsync(hwnd, SW_RESTORE)

        cur_thread = kernel32.GetCurrentThreadId()
        fore_hwnd = user32.GetForegroundWindow()
        fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None) if fore_hwnd else 0

        attached = False
        if fore_thread and cur_thread != fore_thread:
            attached = bool(user32.AttachThreadInput(cur_thread, fore_thread, True))

        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)

        if attached:
            user32.AttachThreadInput(cur_thread, fore_thread, False)
        return True
    except Exception as e:
        logger.debug(f"force_foreground_window error on HWND={hwnd}: {e}")
        return False


def find_app_windows(keywords: list[str]) -> list[tuple[int, str, int]]:
    """
    Find top-level HWNDs matching keywords either by window title or process name on Default desktop.
    Returns list of (hwnd, title, pid).
    """
    ensure_interactive_desktop()
    matching_pids = set()
    kw_lowers = [k.lower().strip() for k in keywords if k.strip()]
    for p in psutil.process_iter():
        try:
            pname = p.name().lower()
            if any(kw in pname for kw in kw_lowers):
                matching_pids.add(p.pid)
        except Exception:
            continue

    candidate_hwnds: list[tuple[int, str, int, int]] = []  # (hwnd, title, pid, score)

    def enum_cb(hwnd, lparam):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        length = user32.GetWindowTextLengthW(hwnd)
        title = ""
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.strip()
        title_lower = title.lower()

        title_match = any(kw in title_lower for kw in kw_lowers)
        pid_match = pid.value in matching_pids

        if title_match or pid_match:
            # Exclude internal helper windows and background system surfaces
            skip_terms = ("msctls_", "default ime", "olemainthreadwndname", "gdi+ window", "msctfime ui", "tooltips_class", "direct3d")
            if not any(skip in title_lower for skip in skip_terms):
                from backend.desktop.window_manager import RECT
                r = RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(r))
                w = r.right - r.left
                h = r.bottom - r.top
                is_vis = bool(user32.IsWindowVisible(hwnd))
                is_icon = bool(user32.IsIconic(hwnd))

                # Real interactive windows must either be iconic, or visible with meaningful area, or have a descriptive title
                if (is_icon or is_vis) and (w >= 200 and h >= 150 or title):
                    # Higher score for explicit title match and larger window area
                    score = (1000 if title_match else 0) + (500 if title else 0) + min(w * h // 1000, 500)
                    candidate_hwnds.append((hwnd, title, pid.value, score))
        return 1

    hdesk = ensure_interactive_desktop()
    cb = WNDENUMPROC(enum_cb)
    if hdesk:
        user32.EnumDesktopWindows(hdesk, cb, 0)
    else:
        user32.EnumWindows(cb, 0)

    # Sort descending by score so real main application windows are prioritized
    candidate_hwnds.sort(key=lambda c: c[3], reverse=True)
    return [(c[0], c[1], c[2]) for c in candidate_hwnds]


def activate_running_app_window(keywords: list[str]) -> bool:
    """
    Search for an already-running process or window matching keywords on Default desktop.
    If found, restores it from tray/background and brings it to the foreground.
    Only returns True if a real, visible main window was successfully brought to foreground.
    """
    candidates = find_app_windows(keywords)
    if candidates:
        for hwnd, title, pid in candidates:
            if force_foreground_window(hwnd):
                # Verify that the restored window is actually visible on screen with size > 100
                r = wintypes.RECT()
                try:
                    user32.GetWindowRect(hwnd, ctypes.pointer(r))
                except Exception:
                    user32.GetWindowRect(hwnd, ctypes.byref(r))
                w = r.right - r.left
                h = r.bottom - r.top
                if user32.IsWindowVisible(hwnd) and w > 100 and h > 100:
                    return True
    return False


def resolve_executable_path(cmd_or_name: str) -> str:
    """Resolves standard executable name or command to absolute path via Registry and common directories."""
    import winreg
    import shutil

    clean = cmd_or_name.strip()
    if os.path.isabs(clean) and os.path.exists(clean) or clean.startswith("http") or clean.endswith(":"):
        return clean

    # 1. Check which (PATH)
    found = shutil.which(clean)
    if found and os.path.exists(found):
        return found

    # 2. Windows App Paths Registry lookup
    for root_key in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(root_key, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{clean}") as key:
                val, _ = winreg.QueryValueEx(key, "")
                if val and os.path.exists(val):
                    return val
        except Exception:
            pass

    # 3. Known application locations on Windows
    known_locations = {
        "chrome.exe": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ],
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ],
        "spotify.exe": [
            os.path.expandvars(r"%LocalAppData%\Microsoft\WindowsApps\Spotify.exe"),
            os.path.expandvars(r"%AppData%\Spotify\Spotify.exe"),
        ],
        "spotify": [
            os.path.expandvars(r"%LocalAppData%\Microsoft\WindowsApps\Spotify.exe"),
            os.path.expandvars(r"%AppData%\Spotify\Spotify.exe"),
        ],
        "discord": [
            os.path.expandvars(r"%LocalAppData%\Discord\Update.exe --processStart Discord.exe"),
        ],
    }
    for candidate in known_locations.get(clean.lower(), []):
        base_exe = candidate.split()[0]
        if os.path.exists(base_exe):
            return candidate

    return clean


def _send_key(vk: int, repeat: int = 1) -> None:
    """Send a Windows virtual keyboard event."""
    try:
        for _ in range(repeat):
            user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
            user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    except Exception as e:
        logger.error(f"Error sending key event vk={vk}: {e}")


def get_clipboard_text() -> Optional[str]:
    """Retrieve text from Windows clipboard natively."""
    try:
        if not user32.OpenClipboard(None):
            return None
        try:
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return None
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                return None
            try:
                return ctypes.c_wchar_p(ptr).value
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()
    except Exception as e:
        logger.error(f"Failed to read Windows clipboard: {e}")
        return None


class SystemToolService:
    """Windows Desktop & System Control Service."""

    APP_MAP = {
        # Web Services & Sites
        "youtube": {"cmd": "https://www.youtube.com", "name": "YouTube", "is_url": True},
        "google": {"cmd": "https://www.google.com", "name": "Google", "is_url": True},
        "browser": {"cmd": "https://www.google.com", "name": "Browser", "is_url": True},
        "gmail": {"cmd": "https://mail.google.com", "name": "Gmail", "is_url": True},
        "github": {"cmd": "https://www.github.com", "name": "GitHub", "is_url": True},
        "reddit": {"cmd": "https://www.reddit.com", "name": "Reddit", "is_url": True},
        "chatgpt": {"cmd": "https://chatgpt.com", "name": "ChatGPT", "is_url": True},
        "netflix": {"cmd": "https://www.netflix.com", "name": "Netflix", "is_url": True},
        "twitter": {"cmd": "https://twitter.com", "name": "X (Twitter)", "is_url": True},

        # System Utilities & Desktop Apps
        "spotify": {"cmd": "spotify:", "name": "Spotify", "process_keywords": ["spotify"]},
        "notepad": {"cmd": "notepad.exe", "name": "Notepad", "process_keywords": ["notepad"]},
        "calculator": {"cmd": "calc.exe", "name": "Calculator", "process_keywords": ["calc"]},
        "calc": {"cmd": "calc.exe", "name": "Calculator", "process_keywords": ["calc"]},
        "chrome": {"cmd": "chrome.exe", "name": "Google Chrome", "process_keywords": ["chrome"]},
        "edge": {"cmd": "msedge.exe", "name": "Microsoft Edge", "process_keywords": ["msedge"]},
        "brave": {"cmd": "brave.exe", "name": "Brave Browser", "process_keywords": ["brave"]},
        "vs code": {"cmd": "code", "name": "Visual Studio Code", "process_keywords": ["code"]},
        "vscode": {"cmd": "code", "name": "Visual Studio Code", "process_keywords": ["code"]},
        "code": {"cmd": "code", "name": "Visual Studio Code", "process_keywords": ["code"]},
        "terminal": {"cmd": "wt.exe", "name": "Windows Terminal"},
        "settings": {"cmd": "ms-settings:", "name": "Windows Settings"},
        "task manager": {"cmd": "taskmgr.exe", "name": "Task Manager", "process_keywords": ["taskmgr"]},
        "paint": {"cmd": "mspaint.exe", "name": "Paint", "process_keywords": ["mspaint"]},
        "explorer": {"cmd": "explorer.exe", "name": "File Explorer"},
        "files": {"cmd": "explorer.exe", "name": "File Explorer"},
        "camera": {"cmd": "microsoft.windows.camera:", "name": "Camera"},
        "discord": {"cmd": "discord:", "name": "Discord", "process_keywords": ["discord"]},
        "steam": {"cmd": "steam:", "name": "Steam", "process_keywords": ["steam"]},
        "whatsapp": {"cmd": "whatsapp:", "name": "WhatsApp", "process_keywords": ["whatsapp"]},
        "word": {"cmd": "winword.exe", "name": "Microsoft Word", "process_keywords": ["winword"]},
        "excel": {"cmd": "excel.exe", "name": "Microsoft Excel", "process_keywords": ["excel"]},
        "powerpoint": {"cmd": "powerpnt.exe", "name": "Microsoft PowerPoint", "process_keywords": ["powerpnt"]},
    }

    # Common aliases, slang, abbreviations, and frequent typing mistakes
    APP_ALIASES = {
        "youtube": [
            "youtube", "you tube", "u tube", "yt", "yotube", "youtub", "yutube",
            "youtbe", "youtube search", "youtube in browser", "youtube search in default browser"
        ],
        "valorant": ["valorant", "valo", "valorent", "volarant", "valrant", "valorents"],
        "google": ["google", "goggle", "google search", "web search"],
        "chrome": ["chrome", "google chrome", "chorme", "crome", "gchrome", "chrom"],
        "edge": ["edge", "microsoft edge", "ms edge"],
        "brave": ["brave", "brave browser"],
        "discord": ["discord", "discrd", "dscord", "discrod", "dc"],
        "spotify": ["spotify", "spotfy", "spotifi", "spoti"],
        "steam": ["steam", "stem", "steem", "stm"],
        "notepad": ["notepad", "notpad", "note pad"],
        "calculator": ["calculator", "calc", "calclator", "calcutor", "calcultor"],
        "settings": ["settings", "setings", "windows settings", "setting"],
        "task manager": ["task manager", "taskmanager", "taskmgr", "task mngr"],
        "terminal": ["terminal", "wt", "windows terminal", "term"],
        "explorer": ["explorer", "file explorer", "files", "my files", "my computer"],
        "camera": ["camera", "cam", "webcam"],
        "paint": ["paint", "mspaint"],
        "word": ["word", "ms word", "microsoft word"],
        "excel": ["excel", "ms excel", "microsoft excel"],
        "powerpoint": ["powerpoint", "power point", "ppt", "slides"],
    }

    @classmethod
    def resolve_app_key(cls, candidate: str) -> str:
        """
        Fuzzy normalization and typo-tolerant resolver for application requests.
        Understands natural human phrasing, slang ('valo', 'yt'), and typos ('chorme', 'valorent').
        """
        import difflib

        clean = candidate.strip().lower()
        clean = re.sub(r"^(?:please\s+)?(?:can you\s+)?(?:open(?:\s+up)?|launch|start|run|go\s+to)\s+", "", clean).strip()
        clean = re.sub(r"\b(in\s+(?:the\s+)?(?:default\s+)?browser|on\s+(?:my\s+)?(?:pc|computer|desktop)|app|game|please)\b", "", clean).strip()

        if not clean:
            return candidate.strip().lower()

        # 1. Exact match in APP_MAP
        if clean in cls.APP_MAP:
            return clean

        # 2. Check APP_ALIASES
        for canonical, aliases in cls.APP_ALIASES.items():
            if clean == canonical or clean in aliases:
                return canonical
            for a in aliases:
                if len(a) >= 3 and (a == clean or clean.startswith(a) or a.startswith(clean)):
                    return canonical

        # 3. Fuzzy close match against all known canonical names
        all_canonicals = list(cls.APP_MAP.keys()) + list(cls.APP_ALIASES.keys())
        close = difflib.get_close_matches(clean, all_canonicals, n=1, cutoff=0.6)
        if close:
            return close[0]

        return clean

    _vision_service: Optional[VisionService] = None
    _rag_service: Optional[RAGService] = None
    _reminder_service: Optional[ReminderService] = None

    @classmethod
    def get_vision_service(cls) -> VisionService:
        if cls._vision_service is None:
            cls._vision_service = VisionService()
        return cls._vision_service

    @classmethod
    def get_rag_service(cls) -> RAGService:
        if cls._rag_service is None:
            cls._rag_service = RAGService()
        return cls._rag_service

    @classmethod
    def get_reminder_service(cls) -> ReminderService:
        if cls._reminder_service is None:
            cls._reminder_service = ReminderService()
        return cls._reminder_service

    @classmethod
    def set_services(
        cls,
        vision: Optional[VisionService] = None,
        rag: Optional[RAGService] = None,
        reminder: Optional[ReminderService] = None,
    ) -> None:
        """Inject mock or configured services for testing and DI."""
        if vision is not None:
            cls._vision_service = vision
        if rag is not None:
            cls._rag_service = rag
        if reminder is not None:
            cls._reminder_service = reminder

    # Volume Controls
    @staticmethod
    def volume_up(steps: int = 5) -> Dict[str, Any]:
        """Increase volume (each step is ~2% in Windows)."""
        _send_key(VK_VOLUME_UP, repeat=steps)
        return {
            "handled": True,
            "action": "volume",
            "type": "volume_up",
            "title": "Volume Increased",
            "message": f"Volume raised by approx {steps * 2}%.",
            "spoken_response": "I've turned up the volume.",
            "data": {"steps": steps, "direction": "up"},
        }

    @staticmethod
    def volume_down(steps: int = 5) -> Dict[str, Any]:
        """Decrease volume (each step is ~2% in Windows)."""
        _send_key(VK_VOLUME_DOWN, repeat=steps)
        return {
            "handled": True,
            "action": "volume",
            "type": "volume_down",
            "title": "Volume Decreased",
            "message": f"Volume lowered by approx {steps * 2}%.",
            "spoken_response": "I've lowered the volume.",
            "data": {"steps": steps, "direction": "down"},
        }

    @staticmethod
    def volume_mute() -> Dict[str, Any]:
        """Toggle mute."""
        _send_key(VK_VOLUME_MUTE, repeat=1)
        return {
            "handled": True,
            "action": "volume",
            "type": "volume_mute",
            "title": "Audio Mute Toggled",
            "message": "Master audio mute was toggled.",
            "spoken_response": "Audio mute toggled.",
            "data": {"direction": "toggle_mute"},
        }

    @staticmethod
    def set_volume_approx(target_percent: int) -> Dict[str, Any]:
        """Adjust volume towards a target percentage."""
        target = max(0, min(100, target_percent))
        # First drop to 0, then raise to target
        _send_key(VK_VOLUME_DOWN, repeat=50)
        steps_up = target // 2
        _send_key(VK_VOLUME_UP, repeat=steps_up)
        return {
            "handled": True,
            "action": "volume",
            "type": "volume_set",
            "title": f"Volume Set to {target}%",
            "message": f"Master volume calibrated to approximately {target}%.",
            "spoken_response": f"Volume set to {target} percent.",
            "data": {"percent": target},
        }

    # Media Playback Controls
    @staticmethod
    def media_play_pause() -> Dict[str, Any]:
        """Toggle media playback."""
        _send_key(VK_MEDIA_PLAY_PAUSE, repeat=1)
        return {
            "handled": True,
            "action": "media",
            "type": "play_pause",
            "title": "Media Play / Pause",
            "message": "Media playback state toggled.",
            "spoken_response": "Playback toggled.",
            "data": {"command": "play_pause"},
        }

    @staticmethod
    def media_next() -> Dict[str, Any]:
        """Skip to next media track."""
        _send_key(VK_MEDIA_NEXT_TRACK, repeat=1)
        return {
            "handled": True,
            "action": "media",
            "type": "next_track",
            "title": "Next Track",
            "message": "Skipped to next media track.",
            "spoken_response": "Playing next track.",
            "data": {"command": "next"},
        }

    @staticmethod
    def media_previous() -> Dict[str, Any]:
        """Return to previous media track."""
        _send_key(VK_MEDIA_PREV_TRACK, repeat=1)
        return {
            "handled": True,
            "action": "media",
            "type": "previous_track",
            "title": "Previous Track",
            "message": "Replaying previous track.",
            "spoken_response": "Playing previous track.",
            "data": {"command": "previous"},
        }

    @staticmethod
    def media_seek_relative(seconds: int) -> Dict[str, Any]:
        """Seek forward or backward by seconds on active media player."""
        from backend.desktop.media_controller import media_controller
        res = media_controller.seek_relative(seconds)
        return {
            "handled": True,
            "action": "media",
            "type": "seek_relative",
            "title": f"Seeked {'Forward' if seconds > 0 else 'Backward'}",
            "message": res.get("message", f"Seeked {seconds} seconds."),
            "spoken_response": res.get("spoken_response", f"Seeked {seconds} seconds."),
            "data": res,
        }

    @staticmethod
    def media_seek_percent(percent: int) -> Dict[str, Any]:
        """Seek to a percentage on timeline scrubber."""
        from backend.desktop.media_controller import media_controller
        res = media_controller.seek_percentage(percent)
        return {
            "handled": True,
            "action": "media",
            "type": "seek_percent",
            "title": f"Seeked to {percent}%",
            "message": res.get("message", f"Seeked to {percent}%."),
            "spoken_response": res.get("spoken_response", f"Seeked to {percent} percent."),
            "data": res,
        }

    @classmethod
    def play_spotify(cls, query: str) -> Dict[str, Any]:
        """Search and play a song on Spotify."""
        from backend.desktop.media_controller import media_controller
        res = media_controller.play_spotify(query)
        return {
            "handled": True,
            "action": "media_play",
            "title": f"Spotify: {query}",
            "message": res.get("message", f"Playing '{query}' on Spotify."),
            "spoken_response": res.get("spoken_response", f"Playing {query} on Spotify."),
            "data": res,
        }

    @classmethod
    def search_spotify(cls, query: str) -> Dict[str, Any]:
        """Search for a song on Spotify."""
        from backend.desktop.media_controller import media_controller
        res = media_controller.search_spotify(query)
        return {
            "handled": True,
            "action": "media_search",
            "title": f"Spotify: {query}",
            "message": res.get("message", f"Searching Spotify for '{query}'."),
            "spoken_response": res.get("spoken_response", f"Searching Spotify for {query}."),
            "data": res,
        }

    # System Diagnostics (Battery, RAM, CPU)
    @staticmethod
    def get_system_battery() -> Dict[str, Any]:
        """Retrieve battery and power state."""
        battery = psutil.sensors_battery()
        if battery is None:
            return {
                "handled": True,
                "action": "battery",
                "title": "Desktop Power",
                "message": "Running on AC mains power (Desktop workstation).",
                "spoken_response": "You are connected to AC power with no battery sensor.",
                "data": {"is_laptop": False, "percent": 100, "plugged": True},
            }

        pct = int(battery.percent)
        plugged = bool(battery.power_plugged)
        status_txt = "Charging / Plugged in" if plugged else "Running on Battery"
        spoken = f"Your battery is at {pct} percent and {'charging' if plugged else 'on battery power'}."

        return {
            "handled": True,
            "action": "battery",
            "title": f"Battery: {pct}%",
            "message": f"{status_txt} ({pct}% remaining)",
            "spoken_response": spoken,
            "data": {"is_laptop": True, "percent": pct, "plugged": plugged},
        }

    @staticmethod
    def get_system_ram_cpu() -> Dict[str, Any]:
        """Retrieve RAM and CPU utilization."""
        ram = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.05)
        total_gb = round(ram.total / (1024**3), 1)
        free_gb = round(ram.available / (1024**3), 1)
        used_gb = round(ram.used / (1024**3), 1)
        used_pct = int(ram.percent)

        spoken = f"CPU usage is {int(cpu)} percent. RAM is at {used_pct} percent with {free_gb} gigabytes free out of {total_gb} gigabytes."

        return {
            "handled": True,
            "action": "system_specs",
            "title": "System Hardware Specs",
            "message": f"RAM: {used_gb}/{total_gb} GB ({used_pct}%) · CPU: {int(cpu)}%",
            "spoken_response": spoken,
            "data": {
                "cpu_percent": cpu,
                "ram_percent": used_pct,
                "ram_free_gb": free_gb,
                "ram_total_gb": total_gb,
            },
        }

    # Dynamic Windows Application & Game Discovery
    @classmethod
    def find_installed_app(cls, app_name: str) -> Optional[tuple[str, str]]:
        """
        Dynamically locate an installed desktop application, game, or shortcut on Windows.
        Returns (full_path, clean_display_name) if found, else None.
        """
        clean = app_name.strip().lower()
        if not clean:
            return None

        # Standard Windows Start Menu, Desktop, and WindowsApps search paths
        search_roots = [
            os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%USERPROFILE%\Desktop"),
            r"C:\Users\Public\Desktop",
            os.path.expandvars(r"%LocalAppData%\Microsoft\WindowsApps"),
            r"C:\Riot Games\Riot Client",
        ]

        valid_exts = {".lnk", ".url", ".exe", ".appref-ms"}
        exact_matches = []
        prefix_matches = []
        substring_matches = []

        for root_dir in search_roots:
            if not os.path.exists(root_dir):
                continue
            try:
                for root, _, files in os.walk(root_dir):
                    if "chrome apps" in root.lower():
                        continue
                    for file in files:
                        base, ext = os.path.splitext(file.lower())
                        if ext not in valid_exts:
                            continue

                        # Filter out uninstallers, crash handlers, updaters, setup utilities
                        if any(skip in base for skip in ("uninstall", "uninst", "setup", "update", "readme", "support", "crash")):
                            continue

                        full_path = os.path.join(root, file)
                        display_name = os.path.splitext(file)[0]

                        if base == clean or (clean == "chrome" and display_name.lower() == "google chrome"):
                            exact_matches.append((full_path, display_name))
                        elif base.startswith(clean) or clean.startswith(base):
                            prefix_matches.append((full_path, display_name))
                        elif clean in base:
                            substring_matches.append((full_path, display_name))
            except Exception as e:
                logger.debug(f"Error scanning {root_dir}: {e}")

        if exact_matches:
            return exact_matches[0]
        if prefix_matches:
            return prefix_matches[0]
        if substring_matches:
            return substring_matches[0]

        return None

    # App Launcher
    @classmethod
    def launch_app(cls, app_key: str) -> Optional[Dict[str, Any]]:
        """Launch an application, game, or system protocol safely under AURA Sandbox Protocol."""
        # 1. Primary Sandbox Gate on raw input
        is_safe_input, reason_input = AuraSandboxProtocol.validate_launch_request(app_key)
        if not is_safe_input:
            logger.warning(f"AURA Sandbox blocked launch request '{app_key}': {reason_input}")
            return {
                "handled": True,
                "action": "sandbox_blocked",
                "type": "security_violation",
                "title": "AURA Sandbox Alert",
                "message": f"Execution blocked: {reason_input}",
                "spoken_response": "That action was blocked by my security sandbox for your safety.",
                "data": {
                    "blocked_target": app_key,
                    "reason": reason_input,
                    "policy": AuraSandboxProtocol.POLICY_VERSION,
                    "status": "BLOCKED",
                },
            }

        resolved_key = cls.resolve_app_key(app_key)

        # 2. Secondary Sandbox Gate on resolved candidate
        is_safe_resolved, reason_resolved = AuraSandboxProtocol.validate_launch_request(resolved_key)
        if not is_safe_resolved:
            logger.warning(f"AURA Sandbox blocked resolved app key '{resolved_key}': {reason_resolved}")
            return {
                "handled": True,
                "action": "sandbox_blocked",
                "type": "security_violation",
                "title": "AURA Sandbox Alert",
                "message": f"Execution blocked: {reason_resolved}",
                "spoken_response": "That action was blocked by my security sandbox for your safety.",
                "data": {
                    "blocked_target": resolved_key,
                    "reason": reason_resolved,
                    "policy": AuraSandboxProtocol.POLICY_VERSION,
                    "status": "BLOCKED",
                },
            }

        info = cls.APP_MAP.get(resolved_key) or cls.APP_MAP.get(app_key.strip().lower())
        if not info:
            # Check for safe word/prefix matches in APP_MAP (avoid matching single letters like 'x')
            for k, val in cls.APP_MAP.items():
                if len(k) >= 3 and (resolved_key.startswith(k) or k.startswith(resolved_key)):
                    info = val
                    break

        # Check if the app is already running and restore it to foreground
        keywords = []
        if info and "process_keywords" in info:
            keywords = info["process_keywords"]
        elif resolved_key in ("spotify", "discord", "valorant", "riot", "chrome", "edge", "notepad", "calculator", "steam"):
            keywords = [resolved_key]

        if keywords and activate_running_app_window(keywords):
            app_title = info.get("name", resolved_key.capitalize()) if info else resolved_key.capitalize()
            return {
                "handled": True,
                "action": "app_launch",
                "title": f"Switched to {app_title}",
                "message": f"Restored {app_title} to your desktop screen.",
                "spoken_response": f"Bringing {app_title} to the front.",
                "data": {"app_name": app_title, "state": "restored"},
            }

        # Check Riot Vanguard anti-cheat service for Valorant
        vgc_warning = ""
        if resolved_key == "valorant":
            try:
                sc_out = subprocess.check_output(
                    ["sc", "query", "vgc"],
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
                ).decode("utf-8", errors="ignore")
                if "RUNNING" not in sc_out:
                    vgc_warning = " (Note: Riot Vanguard anti-cheat service is currently stopped)"
            except Exception as e:
                logger.debug(f"Vanguard check note: {e}")

        ensure_interactive_desktop()
        user32.AllowSetForegroundWindow(-1)

        si = subprocess.STARTUPINFO()
        si.lpDesktop = r"WinSta0\Default"
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = SW_SHOWNORMAL

        if info:
            cmd = info.get("cmd", "")
            is_url = bool(info.get("is_url"))
            name = info.get("name", resolved_key.capitalize())

            # 3. Target Command Sandbox Validation
            is_cmd_safe, cmd_reason = AuraSandboxProtocol.validate_launch_request(cmd, is_url=is_url)
            if not is_cmd_safe:
                logger.warning(f"AURA Sandbox blocked command '{cmd}' for '{name}': {cmd_reason}")
                return {
                    "handled": True,
                    "action": "sandbox_blocked",
                    "type": "security_violation",
                    "title": "AURA Sandbox Alert",
                    "message": f"Execution blocked: {cmd_reason}",
                    "spoken_response": "That action was blocked by my security sandbox for your safety.",
                    "data": {
                        "blocked_target": cmd,
                        "reason": cmd_reason,
                        "policy": AuraSandboxProtocol.POLICY_VERSION,
                        "status": "BLOCKED",
                    },
                }

            try:
                resolved_cmd = resolve_executable_path(cmd)
                if is_url or resolved_cmd.startswith("http") or resolved_cmd.endswith(":") or resolved_cmd.lower().endswith(".lnk") or resolved_cmd.lower().endswith(".url"):
                    os.startfile(resolved_cmd)
                else:
                    work_dir = os.path.dirname(resolved_cmd) if os.path.isabs(resolved_cmd) and os.path.exists(resolved_cmd) else None
                    args = [resolved_cmd]
                    # Pass default start URL for browsers to force an interactive window to open
                    if any(b in resolved_cmd.lower() for b in ("chrome.exe", "msedge.exe", "brave.exe")):
                        args.append("https://www.google.com")
                    subprocess.Popen(args, cwd=work_dir, startupinfo=si)

                return {
                    "handled": True,
                    "action": "app_launch",
                    "title": f"Launched {name}",
                    "message": f"Opening {name} on your desktop.",
                    "spoken_response": f"Opening {name}.",
                    "data": {"app_name": name, "cmd": resolved_cmd},
                }
            except Exception as e:
                logger.error(f"Failed to launch app {name} via APP_MAP: {e}")
                # Fall through to dynamic scanner if APP_MAP failed

        # Dynamic Windows System Search for games / installed apps (e.g. Valorant, Discord, Steam, etc.)
        installed = cls.find_installed_app(resolved_key) or cls.find_installed_app(app_key)
        if installed:
            path, display_name = installed

            # 4. Boundary & Binary Sandbox Gate on discovered path
            is_path_safe, path_reason = AuraSandboxProtocol.validate_executable_path(path)
            if not is_path_safe:
                logger.warning(f"AURA Sandbox blocked discovered application path '{path}': {path_reason}")
                return {
                    "handled": True,
                    "action": "sandbox_blocked",
                    "type": "security_violation",
                    "title": "AURA Sandbox Alert",
                    "message": f"Execution blocked: {path_reason}",
                    "spoken_response": "That action was blocked by my security sandbox for your safety.",
                    "data": {
                        "blocked_target": path,
                        "reason": path_reason,
                        "policy": AuraSandboxProtocol.POLICY_VERSION,
                        "status": "BLOCKED",
                    },
                }

            try:
                os.startfile(path)
                spoken = f"Opening {display_name}."
                if vgc_warning:
                    spoken = f"Opening {display_name}. Note that Riot Vanguard anti-cheat is currently stopped on your PC."

                return {
                    "handled": True,
                    "action": "app_launch",
                    "title": f"Launched {display_name}",
                    "message": f"Opening {display_name} on your desktop.{vgc_warning}",
                    "spoken_response": spoken,
                    "data": {"app_name": display_name, "path": path, "vgc_status": "STOPPED" if vgc_warning else "OK"},
                }
            except Exception as e:
                logger.error(f"Failed to open discovered app {path}: {e}")
                return {
                    "handled": True,
                    "action": "app_launch",
                    "title": f"Failed to Open {display_name}",
                    "message": f"Could not launch application: {e}",
                    "spoken_response": f"Sorry, I had trouble opening {display_name}.",
                    "data": {"app_name": display_name, "error": str(e)},
                }

        # If not found anywhere on the system, return handled: True with clean not found message
        # This completely prevents LLM from hallucinating that the app is open!
        formatted_name = resolved_key.title()
        return {
            "handled": True,
            "action": "app_launch",
            "title": f"App Not Found: {formatted_name}",
            "message": f"I couldn't find an installed application or game named '{formatted_name}' on this PC.",
            "spoken_response": f"I couldn't find {resolved_key} installed on your PC.",
            "data": {"app_name": resolved_key, "found": False},
        }

    # Window Management & Application Control
    @classmethod
    def minimize_app(cls, app_key: str) -> Dict[str, Any]:
        """Minimize an application's window."""
        resolved = cls.resolve_app_key(app_key)
        candidates = find_app_windows([resolved, app_key.strip().lower()])
        if not candidates:
            return {
                "handled": True,
                "action": "window_management",
                "title": f"Window Not Found: {app_key.title()}",
                "message": f"Could not find an open window for '{app_key.title()}'.",
                "spoken_response": f"I couldn't find an open window for {app_key}.",
                "data": {"success": False},
            }
        hwnd, title, _ = candidates[0]
        user32.ShowWindow(hwnd, SW_MINIMIZE)
        return {
            "handled": True,
            "action": "window_management",
            "type": "minimize",
            "title": f"Minimized {title}",
            "message": f"Minimized window '{title}'.",
            "spoken_response": f"Minimized {app_key}.",
            "data": {"hwnd": hwnd, "title": title, "action": "minimize"},
        }

    @classmethod
    def maximize_app(cls, app_key: str) -> Dict[str, Any]:
        """Maximize an application's window."""
        resolved = cls.resolve_app_key(app_key)
        candidates = find_app_windows([resolved, app_key.strip().lower()])
        if not candidates:
            return {
                "handled": True,
                "action": "window_management",
                "title": f"Window Not Found: {app_key.title()}",
                "message": f"Could not find an open window for '{app_key.title()}'.",
                "spoken_response": f"I couldn't find an open window for {app_key}.",
                "data": {"success": False},
            }
        hwnd, title, _ = candidates[0]
        user32.ShowWindow(hwnd, SW_MAXIMIZE)
        user32.SetForegroundWindow(hwnd)
        return {
            "handled": True,
            "action": "window_management",
            "type": "maximize",
            "title": f"Maximized {title}",
            "message": f"Maximized window '{title}'.",
            "spoken_response": f"Maximized {app_key}.",
            "data": {"hwnd": hwnd, "title": title, "action": "maximize"},
        }

    @classmethod
    def close_app(cls, app_key: str) -> Dict[str, Any]:
        """Safely close an application by sending WM_CLOSE to its top-level window."""
        resolved = cls.resolve_app_key(app_key)
        candidates = find_app_windows([resolved, app_key.strip().lower()])
        if not candidates:
            return {
                "handled": True,
                "action": "app_close",
                "title": f"App Not Running: {app_key.title()}",
                "message": f"Could not find an active window for '{app_key.title()}'.",
                "spoken_response": f"{app_key} is not currently running.",
                "data": {"success": False},
            }
        hwnd, title, pid = candidates[0]
        # WM_CLOSE = 0x0010
        user32.PostMessageW(hwnd, 0x0010, 0, 0)
        return {
            "handled": True,
            "action": "app_close",
            "title": f"Closed {title}",
            "message": f"Sent close command to '{title}'.",
            "spoken_response": f"Closed {app_key}.",
            "data": {"hwnd": hwnd, "title": title, "pid": pid},
        }

    @classmethod
    def get_active_window(cls) -> Dict[str, Any]:
        """Retrieve information about the active foreground window."""
        ensure_interactive_desktop()
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return {
                "handled": True,
                "action": "active_window",
                "title": "Desktop Active",
                "message": "Desktop is currently focused.",
                "spoken_response": "The desktop is currently active.",
                "data": {"title": "Desktop"},
            }
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or "Untitled Window"

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        pname = psutil.Process(pid.value).name() if psutil.pid_exists(pid.value) else "Unknown"

        return {
            "handled": True,
            "action": "active_window",
            "title": f"Active: {title}",
            "message": f"Focused Application: {pname} (PID: {pid.value}) · Title: '{title}'",
            "spoken_response": f"The currently active window is {title}.",
            "data": {"hwnd": hwnd, "title": title, "process": pname, "pid": pid.value},
        }

    @classmethod
    def list_running_apps(cls) -> Dict[str, Any]:
        """List running top-level application windows on Default desktop."""
        ensure_interactive_desktop()
        apps: list[dict] = []

        def enum_cb(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value
                    if not any(skip in title.lower() for skip in ("program manager", "windows input experience", "twinkle tray panel", "msctls_")):
                        pid = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        pname = psutil.Process(pid.value).name() if psutil.pid_exists(pid.value) else "Unknown"
                        apps.append({"hwnd": hwnd, "title": title, "process": pname, "pid": pid.value})
            return 1

        hdesk = ensure_interactive_desktop()
        cb = WNDENUMPROC(enum_cb)
        if hdesk:
            user32.EnumDesktopWindows(hdesk, cb, 0)
        else:
            user32.EnumWindows(cb, 0)

        app_names = [a["process"].replace(".exe", "").capitalize() for a in apps[:8]]
        spoken = f"You have {len(apps)} active application windows open, including {', '.join(app_names[:4])}."

        return {
            "handled": True,
            "action": "running_apps",
            "title": f"Running Applications ({len(apps)})",
            "message": f"Active Windows: {', '.join(a['title'] for a in apps[:6])}",
            "spoken_response": spoken,
            "data": {"count": len(apps), "apps": apps},
        }

    # Clipboard Inspection & Summary
    @staticmethod
    def inspect_clipboard() -> Dict[str, Any]:
        """Read and summarize current Windows clipboard."""
        text = get_clipboard_text()
        if not text or not text.strip():
            return {
                "handled": True,
                "action": "clipboard",
                "title": "Clipboard Empty",
                "message": "Your clipboard does not contain any text.",
                "spoken_response": "Your clipboard is currently empty.",
                "data": {"has_text": False, "length": 0},
            }

        clean = text.strip()
        word_count = len(clean.split())
        preview = clean[:180] + ("…" if len(clean) > 180 else "")

        if word_count < 25:
            spoken = f"Your clipboard contains: {clean}"
        else:
            spoken = f"Your clipboard contains a {word_count} word excerpt starting with: {clean[:80]}."

        return {
            "handled": True,
            "action": "clipboard",
            "title": f"Clipboard ({word_count} words)",
            "message": preview,
            "spoken_response": spoken,
            "data": {
                "has_text": True,
                "full_text": clean,
                "preview": preview,
                "word_count": word_count,
            },
        }

    # Web & Search Actions
    @staticmethod
    def search_youtube(query: str) -> Dict[str, Any]:
        """Open YouTube search in default browser under sandbox rules."""
        is_safe, _ = AuraSandboxProtocol.sanitize_shell_command(query)
        if not is_safe:
            clean_q = re.sub(r"[&|;><`$\r\n\x00]", "", query).strip()
        else:
            clean_q = query.strip()

        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(clean_q)}"
        is_url_safe, reason = AuraSandboxProtocol.validate_url(url)
        if not is_url_safe:
            return {
                "handled": True,
                "action": "sandbox_blocked",
                "title": "AURA Sandbox Alert",
                "message": f"Search URL blocked: {reason}",
                "spoken_response": "That search action was blocked by my security sandbox.",
                "data": {"query": clean_q, "reason": reason, "status": "BLOCKED"},
            }

        webbrowser.open(url)
        return {
            "handled": True,
            "action": "web_search",
            "title": f"YouTube: {clean_q}",
            "message": f"Opened YouTube search for '{clean_q}'.",
            "spoken_response": f"Searching YouTube for {clean_q}.",
            "data": {"platform": "youtube", "query": clean_q, "url": url},
        }

    @staticmethod
    def search_google(query: str) -> Dict[str, Any]:
        """Open Google search in default browser under sandbox rules."""
        is_safe, _ = AuraSandboxProtocol.sanitize_shell_command(query)
        if not is_safe:
            clean_q = re.sub(r"[&|;><`$\r\n\x00]", "", query).strip()
        else:
            clean_q = query.strip()

        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(clean_q)}"
        is_url_safe, reason = AuraSandboxProtocol.validate_url(url)
        if not is_url_safe:
            return {
                "handled": True,
                "action": "sandbox_blocked",
                "title": "AURA Sandbox Alert",
                "message": f"Search URL blocked: {reason}",
                "spoken_response": "That search action was blocked by my security sandbox.",
                "data": {"query": clean_q, "reason": reason, "status": "BLOCKED"},
            }

        webbrowser.open(url)
        return {
            "handled": True,
            "action": "web_search",
            "title": f"Google: {clean_q}",
            "message": f"Opened Google search for '{clean_q}'.",
            "spoken_response": f"Searching Google for {clean_q}.",
            "data": {"platform": "google", "query": clean_q, "url": url},
        }

    # Phase 8: Screen Vision & Desktop Awareness
    @classmethod
    def capture_and_analyze_screen(cls, prompt: str) -> Dict[str, Any]:
        """Capture active screen and analyze with multimodal vision or Windows Media OCR."""
        ensure_interactive_desktop()
        vsvc = cls.get_vision_service()
        screenshot = vsvc.capture_screen()
        active_window = screenshot.get("window_title") or screenshot.get("active_window") or "Desktop"
        image_path = screenshot.get("image_path", "")
        summary = vsvc.analyze_screen_sync(image_path, prompt, active_window)

        return {
            "handled": True,
            "action": "screen_vision",
            "type": "screen_vision",
            "title": f"Screen: {active_window}",
            "message": summary,
            "spoken_response": summary,
            "data": {
                "active_window": active_window,
                "thumbnail_base64": screenshot.get("thumbnail") or screenshot.get("thumbnail_base64", ""),
                "image_path": image_path,
                "timestamp": screenshot.get("timestamp", 0),
                "width": screenshot.get("width", 1920),
                "height": screenshot.get("height", 1080),
                "details": summary,
            },
        }

    # Phase 9: Local Document Q&A (RAG)
    @classmethod
    def search_documents(cls, query: str) -> Dict[str, Any]:
        """Search local documents with keyword/BM25 relevance."""
        rag = cls.get_rag_service()
        chunks = rag.search(query, top_k=3)
        if not chunks:
            msg = f"I didn't find any relevant notes matching '{query}' in your local documents."
            return {
                "handled": True,
                "action": "document_search",
                "type": "document_search",
                "title": f"Document Search: {query}",
                "message": msg,
                "spoken_response": msg,
                "data": {"query": query, "count": 0, "chunks": []},
            }

        doc_names = list(dict.fromkeys(c["doc_name"] for c in chunks))
        top_snippet = chunks[0]["snippet"].strip().replace("\n", " ")
        if len(top_snippet) > 140:
            top_snippet = top_snippet[:140] + "…"
        spoken = f"Found relevant information in {', '.join(doc_names)}: {top_snippet}"
        return {
            "handled": True,
            "action": "document_search",
            "type": "document_search",
            "title": f"Document Knowledge: {query}",
            "message": f"Found {len(chunks)} relevant excerpt(s) in {', '.join(doc_names)}.",
            "spoken_response": spoken,
            "data": {
                "query": query,
                "count": len(chunks),
                "chunks": chunks,
                "documents": doc_names,
            },
        }

    @classmethod
    def reindex_documents(cls) -> Dict[str, Any]:
        """Re-scan and index documents in backend/data/documents/."""
        rag = cls.get_rag_service()
        count = rag.index_directory()
        msg = f"Re-indexed local documents: {count} knowledge chunk(s) indexed."
        return {
            "handled": True,
            "action": "document_search",
            "type": "document_reindex",
            "title": "Documents Re-indexed",
            "message": msg,
            "spoken_response": f"I've re-indexed your local documents. {count} knowledge chunks are ready.",
            "data": {"count": count},
        }

    # Phase 10: Reminders & Timers
    @classmethod
    def handle_timer_command(cls, prompt: str) -> Optional[Dict[str, Any]]:
        """Parse and execute timer/reminder command."""
        rsvc = cls.get_reminder_service()
        cmd = rsvc.parse_command(prompt)
        if not cmd:
            return None
        res = rsvc.execute_command(prompt)
        if not res or not res.get("handled"):
            return None
        return {
            "handled": True,
            "action": "timer",
            "type": res.get("action", "timer"),
            "title": res.get("title", "Timer"),
            "message": res.get("message", ""),
            "spoken_response": res.get("spoken_response", res.get("message", "")),
            "data": res.get("data", {}),
        }

    # Fast Natural Language Intent Classifier
    @classmethod
    def execute_intent(cls, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Interprets conversational user prompts into Windows system actions.
        Runs sub-millisecond regex parsing before LLM invocation.
        """
        p = prompt.strip().lower()

        # 0. Timers & Reminders (Phase 10 & V1 Email System)
        timer_res = cls.handle_timer_command(prompt)
        if timer_res:
            return timer_res

        # 0. Important Notes & Email Notifications (Phase V1 Email Notifications)
        if re.search(r"\b(?:send\s+(?:me\s+)?a\s+)?test\s+email\b", p):
            from backend.services.email_service import email_service
            res = email_service.send_test_email()
            msg = res.get("message") if res.get("success") else f"Failed to send test email: {res.get('error')}"
            return {
                "handled": True,
                "action": "test_email",
                "title": "Test Email",
                "message": msg,
                "spoken_response": msg,
                "data": res,
            }

        if re.search(r"\b(?:send|email)\s+(?:me\s+)?(?:my\s+)?daily\s+summary\b", p):
            from backend.services.daily_summary_service import daily_summary_service
            res = daily_summary_service.send_summary_now()
            msg = "Sent your daily summary email." if res.get("success") else f"Could not send daily summary: {res.get('error')}"
            return {
                "handled": True,
                "action": "daily_summary",
                "title": "Daily Summary",
                "message": msg,
                "spoken_response": msg,
                "data": res,
            }

        m_email_note = re.search(r"\b(?:this\s+is\s+important[.,]?\s*(?:email\s+(?:it\s+to\s+me|me))?|email\s+(?:this\s+to\s+me|this\s+information))\s*(?::\s*|\s+that\s+|\s+about\s+)?(.*)$", p)
        if m_email_note and m_email_note.group(1).strip():
            content = m_email_note.group(1).strip()
            from backend.services.important_notes_service import important_notes_service
            from backend.services.email_service import email_service
            note = important_notes_service.add_note(content, emailed=True)
            res = email_service.send_email(
                subject="📌 Important Note from AURA",
                body_text=f"Important Information:\n\n{content}",
            )
            msg = "Saved note and emailed it to you." if res.get("success") else f"Saved note. (Email dispatch note: {res.get('error')})"
            return {
                "handled": True,
                "action": "important_note_email",
                "title": "Important Note Saved & Emailed",
                "message": msg,
                "spoken_response": msg,
                "data": {"note": note, "email": res},
            }

        m_save_note = re.search(r"\b(?:save\s+this\s+as\s+an?\s+important\s+note|save\s+important\s+note)\s*(?::\s*|\s+that\s+|\s+about\s+)?(.*)$", p)
        if m_save_note:
            content = m_save_note.group(1).strip() or prompt.strip()
            from backend.services.important_notes_service import important_notes_service
            note = important_notes_service.add_note(content, emailed=False)
            msg = "Saved this as an important note."
            return {
                "handled": True,
                "action": "save_important_note",
                "title": "Important Note Saved",
                "message": f"Saved: '{content}'",
                "spoken_response": msg,
                "data": {"note": note},
            }

        # 0. Screen Vision & Desktop Awareness (Phase 8 - Fast In-Memory OCR & Scene Perception)
        if re.search(
            r"\b(look\s+at\s+(?:my\s+)?screen|what(?:'s|\s+is)\s+(?:on|written|text\s+on)\s+(?:my\s+)?screen|read\s+(?:the\s+)?(?:text|words?|content)?\s*(?:on\s+)?(?:my\s+)?screen|ocr\s+(?:my\s+)?screen|screen\s+text|read\s+(?:my\s+)?screen|capture\s+screen|take\s+a\s+screenshot|analyze\s+(?:my\s+)?screen|check\s+(?:my\s+)?screen|see\s+(?:my\s+)?screen)\b",
            p,
        ):
            return cls.capture_and_analyze_screen(prompt)

        # 0. Local Document Q&A / Re-indexing (Phase 9)
        doc_search_m = re.search(r"\b(?:search\s+(?:my\s+)?documents?\s+(?:for|about)?|what\s+do\s+(?:my\s+)?notes?\s+say\s+about|look\s+up\s+in\s+(?:my\s+)?documents?|find\s+in\s+(?:my\s+)?notes?)\s+(.+)$", p)
        if doc_search_m:
            return cls.search_documents(doc_search_m.group(1).strip())
        if re.search(r"\b(re-?index\s+(?:my\s+)?documents?|index\s+(?:my\s+)?documents?|scan\s+(?:my\s+)?documents?)\b", p):
            return cls.reindex_documents()

        # 1. Volume Mute
        if re.search(r"\b(mute\s+(audio|sound|volume)?|unmute|toggle\s+mute)\b", p):
            return cls.volume_mute()

        # 2. Volume Exact Set (e.g. "set volume to 60%")
        set_vol_m = re.search(r"\b(?:set|turn|change)\s+(?:the\s+)?volume\s+(?:to\s+)?(\d{1,3})\s*(?:%|percent)?\b", p)
        if set_vol_m:
            pct = int(set_vol_m.group(1))
            return cls.set_volume_approx(pct)

        # 3. Volume Up
        if re.search(r"\b(volume\s+up|increase\s+volume|turn\s+up\s+(the\s+)?volume|raise\s+(the\s+)?volume|louder)\b", p):
            return cls.volume_up(5)

        # 4. Volume Down
        if re.search(r"\b(volume\s+down|decrease\s+volume|turn\s+down\s+(the\s+)?volume|lower\s+(the\s+)?volume|quieter)\b", p):
            return cls.volume_down(5)

        # 5. Media Play / Pause (Handles "play it", "resume", "pause", "toggle play")
        if re.search(r"^(?:please\s+)?(?:can you\s+)?(?:play\s+it|resume\s+it|resume|play\s+pause|toggle\s+play|pause\s+playback|play\s+playback|pause|stop\s+playback|stop\s+playing)$", p) or re.search(r"\b(pause\s+music|pause\s+video|play\s+music|resume\s+music|toggle\s+play|pause\s+playback|play\s+playback)\b", p):
            return cls.media_play_pause()

        # 6. Media Next Track
        if re.search(r"^(?:please\s+)?(?:can you\s+)?(?:next\s+song|next\s+track|next\s+video|next|skip\s+song|skip\s+track|skip)$", p):
            return cls.media_next()

        # 7. Media Previous Track
        if re.search(r"^(?:please\s+)?(?:can you\s+)?(?:previous\s+song|previous\s+track|previous\s+video|previous|prev\s+song|prev\s+track|prev|replay\s+song|last\s+song)$", p):
            return cls.media_previous()

        # 7b. Timeline Controller / Seeking
        seek_fwd_m = re.search(r"\b(?:forward|fast\s+forward|skip\s+forward|go\s+forward)\s+(?:by\s+)?(\d+)\s*(?:s|sec|secs|seconds)?\b", p)
        if seek_fwd_m:
            return cls.media_seek_relative(int(seek_fwd_m.group(1)))

        seek_back_m = re.search(r"\b(?:rewind|backward|back|go\s+back|skip\s+backward|skip\s+back)\s+(?:by\s+)?(\d+)\s*(?:s|sec|secs|seconds)?\b", p)
        if seek_back_m:
            return cls.media_seek_relative(-int(seek_back_m.group(1)))

        seek_pct_m = re.search(r"\b(?:seek|go|jump|scrub)\s+(?:to\s+)?(\d{1,3})\s*(?:%|\bpercent\b)", p)
        if seek_pct_m:
            return cls.media_seek_percent(int(seek_pct_m.group(1)))

        # 8. Battery Diagnostics
        if re.search(r"\b(battery|battery\s+level|battery\s+percentage|how\s+much\s+battery|charger\s+plugged)\b", p):
            return cls.get_system_battery()

        # 9. RAM / CPU Diagnostics
        if re.search(r"\b(ram\s+usage|memory\s+usage|cpu\s+usage|system\s+specs|how\s+much\s+ram)\b", p):
            return cls.get_system_ram_cpu()

        # 10. Clipboard Actions
        if re.search(r"\b(clipboard|summarize\s+(my\s+)?clipboard|read\s+(my\s+)?clipboard|what(?:'s|\s+is)\s+on\s+my\s+clipboard)\b", p):
            return cls.inspect_clipboard()

        # 11. Spotify Actions & Search ("open spotify and play ...", "play ... on spotify", "search ... on spotify", etc.)
        spot_play_m = re.search(
            r"\b(?:open\s+(?:the\s+)?spotify\s+(?:and\s+)?play\s+(.+)|play\s+(.+?)\s+(?:in|on)\s+spotify|spotify\s+play\s+(.+)|search\s+(.+?)\s+(?:in|on)\s+spotify\s+and\s+play)\b",
            p,
            re.IGNORECASE,
        )
        if spot_play_m:
            q = (spot_play_m.group(1) or spot_play_m.group(2) or spot_play_m.group(3) or spot_play_m.group(4) or "").strip()
            clean_q = re.sub(r"\b(song|music|track|album|please)\b", "", q, flags=re.IGNORECASE).strip() or q.strip()
            return cls.play_spotify(clean_q)

        spot_search_m = re.search(
            r"\b(?:open\s+(?:the\s+)?spotify\s+(?:and\s+)?search(?:\s+for)?\s+(.+)|search\s+(.+?)\s+(?:in|on)\s+spotify|spotify\s+search(?:\s+for)?\s+(.+))\b",
            p,
            re.IGNORECASE,
        )
        if spot_search_m:
            q = (spot_search_m.group(1) or spot_search_m.group(2) or spot_search_m.group(3) or "").strip()
            return cls.search_spotify(q)

        # 12. YouTube Actions & Search (handles "open yt and search for ...", "play ... in yt", etc.)
        yt_search_m = re.search(
            r"\b(?:search\s+(?:on\s+|in\s+)?(?:youtube|yt)\s+(?:for\s+)?|open\s+(?:the\s+)?(?:youtube|yt)\s+(?:and\s+search(?:\s+for)?|to\s+search(?:\s+for)?)\s+|play\s+(.+)\s+(?:on|in)\s+(?:youtube|yt)|(?:youtube|yt)\s+search\s+(?:for\s+)?)\s*(.*)$",
            p,
            re.IGNORECASE,
        )
        if yt_search_m:
            query = (yt_search_m.group(1) or yt_search_m.group(2) or "").strip()
            query = re.sub(r"\b(in\s+(?:default\s+)?browser|on\s+desktop|song|video|track|please)\b", "", query, flags=re.IGNORECASE).strip()
            if query:
                return cls.search_youtube(query)
            else:
                return cls.launch_app("youtube")

        if re.search(r"^(?:open|launch|go\s+to|start)\s+(?:the\s+)?(?:youtube|you\s*tube|u\s*tube|yt)(?:\s+search)?(?:\s+in\s+(?:default\s+)?browser|\s+app|\s+for me|\s+please)?$", p, re.IGNORECASE):
            return cls.launch_app("youtube")

        # 13. Google Search
        # Handles "search python tutorials on google", "search for python tutorials in google",
        #         "google python tutorials", "google search python tutorials", "search google for python tutorials"
        g_m = re.search(
            r"\b(?:search\s+(?:for\s+)?(.+?)\s+(?:on|in|using)\s+google|(?:open\s+(?:the\s+)?google\s+and\s+search(?:\s+for)?\s+(.+))|(?:google\s+search\s+(?:for\s+)?|search\s+google\s+(?:for\s+)?|google\s+)(.+))\b",
            p,
            re.IGNORECASE,
        )
        if g_m:
            q = (g_m.group(1) or g_m.group(2) or g_m.group(3) or "").strip()
            if q and not q.startswith("what is your") and not q.startswith("who are you"):
                return cls.search_google(q)

        # 13. App Launcher ("open spotify", "launch notepad", "open valorant", etc.)
        app_m = re.search(r"^(?:please\s+)?(?:can you\s+)?(?:open(?:\s+up)?|launch|start|run|go\s+to)\s+([a-zA-Z0-9\s]+?)(?:\s+app|\s+game|\s+for me|\s+please)?$", p)
        if app_m:
            candidate = app_m.group(1).strip()
            candidate = re.sub(r"^(the|a|an)\s+", "", candidate).strip()
            if candidate and candidate not in ("my documents", "screen", "my screen", "notes", "my notes", "camera"):
                res = cls.launch_app(candidate)
                if res:
                    return res

        return None
