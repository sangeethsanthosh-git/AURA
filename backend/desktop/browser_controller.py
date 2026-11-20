"""
AURA Browser Controller
Provides intelligent web browser control across Chrome, Edge, Firefox, and default browsers.
Supports smart searches, tab switching, address navigation, and page scrolling.
Enforces SSRF prevention and zero-trust URI allowlisting.
"""

from typing import Dict, Any, Optional
import webbrowser
import urllib.parse
import time
import logging
from backend.desktop.mouse_controller import mouse_controller
from backend.desktop.keyboard_controller import keyboard_controller
from backend.desktop.window_manager import window_manager
from backend.security.network_guard import network_guard

logger = logging.getLogger(__name__)


class BrowserController:
    """Controls installed web browsers and executes web search workflows."""

    def open_url(self, url: str) -> Dict[str, Any]:
        """Safely opens a validated URL in the user's default browser, ensuring a visible window is created."""
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        # Zero-Trust SSRF Validation
        is_safe, reason = network_guard.is_ssrf_safe(url)
        if not is_safe:
            return {"success": False, "error": f"URL blocked by security guard: {reason}"}

        try:
            import os
            import subprocess
            # Try launching Chrome or Edge directly with the URL to force an interactive window to appear
            # even if background processes exist in Task Manager
            browser_binaries = (
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            )
            launched = False
            for b_exe in browser_binaries:
                if os.path.exists(b_exe):
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    si.wShowWindow = 1  # SW_SHOWNORMAL
                    subprocess.Popen([b_exe, url], startupinfo=si)
                    launched = True
                    break

            if not launched:
                webbrowser.open(url, new=2)

            time.sleep(1.0)
            return {"success": True, "url": url}
        except Exception as e:
            logger.error(f"Error opening browser URL: {e}")
            try:
                webbrowser.open(url, new=2)
                return {"success": True, "url": url}
            except Exception as e2:
                return {"success": False, "error": str(e2)}

    def search_youtube(self, query: str) -> Dict[str, Any]:
        """Searches YouTube and navigates to the results page."""
        encoded = urllib.parse.quote_plus(query.strip())
        url = f"https://www.youtube.com/results?search_query={encoded}"
        res = self.open_url(url)
        return {
            "success": res.get("success", False),
            "platform": "youtube",
            "query": query,
            "url": url,
        }

    def search_google(self, query: str) -> Dict[str, Any]:
        """Searches Google and navigates to the results page."""
        encoded = urllib.parse.quote_plus(query.strip())
        url = f"https://www.google.com/search?q={encoded}"
        res = self.open_url(url)
        return {
            "success": res.get("success", False),
            "platform": "google",
            "query": query,
            "url": url,
        }

    def new_tab(self) -> bool:
        """Opens a new browser tab (Ctrl+T)."""
        self._ensure_browser_focus()
        return keyboard_controller.hotkey("ctrl", "t")

    def close_tab(self) -> bool:
        """Closes the current browser tab (Ctrl+W)."""
        self._ensure_browser_focus()
        return keyboard_controller.hotkey("ctrl", "w")

    def reopen_tab(self) -> bool:
        """Reopens last closed tab (Ctrl+Shift+T)."""
        self._ensure_browser_focus()
        return keyboard_controller.hotkey("ctrl", "shift", "t")

    def next_tab(self) -> bool:
        """Switches to the next browser tab (Ctrl+Tab)."""
        self._ensure_browser_focus()
        return keyboard_controller.hotkey("ctrl", "tab")

    def previous_tab(self) -> bool:
        """Switches to the previous browser tab (Ctrl+Shift+Tab)."""
        self._ensure_browser_focus()
        return keyboard_controller.hotkey("ctrl", "shift", "tab")

    def scroll_down(self, steps: int = 4) -> bool:
        """Scrolls page down smoothly."""
        self._ensure_browser_focus()
        return mouse_controller.scroll(-steps)

    def scroll_up(self, steps: int = 4) -> bool:
        """Scrolls page up smoothly."""
        self._ensure_browser_focus()
        return mouse_controller.scroll(steps)

    def navigate_address_bar(self, url: str) -> bool:
        """Focuses address bar (Ctrl+L), types URL, and presses Enter."""
        self._ensure_browser_focus()
        keyboard_controller.hotkey("ctrl", "l")
        time.sleep(0.1)
        keyboard_controller.type_text(url)
        time.sleep(0.05)
        return keyboard_controller.press_key("enter")

    @staticmethod
    def _ensure_browser_focus() -> bool:
        """Ensures an active browser window (Chrome, Edge, Firefox, Brave) has foreground focus."""
        for b in ("chrome", "msedge", "firefox", "brave"):
            win = window_manager.find_window(b)
            if win and win.get("hwnd"):
                return window_manager.focus_window(win["hwnd"])
        return False


# Global browser controller instance
browser_controller = BrowserController()
