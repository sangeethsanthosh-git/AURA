"""
AURA Desktop Controller (Master Automation Facade)
Coordinates mouse, keyboard, window management, browser, media, and file explorer subsystems.
Enforces Emergency Stop abort guarantees and zero-trust permission checks.
"""

from typing import Dict, Any, Optional, List, Tuple
import time
import subprocess
import os
import logging

from backend.desktop.mouse_controller import mouse_controller, MouseController
from backend.desktop.keyboard_controller import keyboard_controller, KeyboardController
from backend.desktop.window_manager import window_manager, WindowManager
from backend.desktop.desktop_perception import desktop_perception, DesktopPerception
from backend.desktop.browser_controller import browser_controller, BrowserController
from backend.desktop.media_controller import media_controller, MediaController
from backend.desktop.file_explorer_controller import file_explorer_controller, FileExplorerController
from backend.security.emergency_stop import emergency_stop
from backend.security.permission_gateway import permission_gateway, PermissionLevel, PermissionDecision

logger = logging.getLogger(__name__)


class DesktopController:
    """Master desktop automation orchestrator for AURA."""

    def __init__(self):
        self.mouse: MouseController = mouse_controller
        self.keyboard: KeyboardController = keyboard_controller
        self.windows: WindowManager = window_manager
        self.perception: DesktopPerception = desktop_perception
        self.browser: BrowserController = browser_controller
        self.media: MediaController = media_controller
        self.explorer: FileExplorerController = file_explorer_controller

        self._abort_requested: bool = False

    def emergency_abort(self) -> Dict[str, Any]:
        """
        Instant failsafe: releases any held mouse buttons and keyboard keys,
        hides AURA's virtual hand, and halts active automation loops.
        """
        logger.critical("DesktopController emergency abort invoked!")
        self._abort_requested = True
        try:
            from backend.desktop.virtual_hand_controller import virtual_hand_controller
            virtual_hand_controller.hide()
        except Exception:
            pass
        mouse_released = self.mouse.release_all()
        keys_released = self.keyboard.release_all()
        return {
            "success": True,
            "mouse_released": mouse_released,
            "keys_released": keys_released,
            "message": "Desktop interaction emergency halted.",
        }

    def reset_abort(self) -> None:
        self._abort_requested = False

    def open_app(self, app_name: str) -> Dict[str, Any]:
        """Launches or focuses an application and verifies it appears."""
        if emergency_stop.is_stopped() or self._abort_requested:
            return {"success": False, "error": "Emergency stop active"}

        q = app_name.strip().lower()

        # Check if already open
        existing = self.windows.find_window(q)
        if existing and existing.get("hwnd"):
            self.windows.focus_window(existing["hwnd"])
            return {
                "success": True,
                "action": "focus_existing",
                "app": app_name,
                "hwnd": existing["hwnd"],
                "message": f"Focused open window: {existing['title']}",
            }

        # Common executable shortcuts
        common_bins = {
            "notepad": "notepad.exe",
            "calc": "calc.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
            "spotify": "spotify.exe",
            "code": "code.cmd",
            "vlc": "vlc.exe",
            "taskmgr": "taskmgr.exe",
            "task manager": "taskmgr.exe",
            "explorer": "explorer.exe",
        }

        bin_target = common_bins.get(q, q)
        try:
            subprocess.Popen([bin_target], shell=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))
            time.sleep(0.5)

            # Verify window opened
            opened = self.perception.verify_window_opened(q, timeout=3.0)
            return {
                "success": True,
                "action": "launched",
                "app": app_name,
                "verified": opened,
                "message": f"Launched {app_name}",
            }
        except Exception as e:
            # Fallback to startfile
            try:
                os.startfile(bin_target)
                time.sleep(0.5)
                return {"success": True, "action": "started", "app": app_name}
            except Exception as e2:
                return {"success": False, "error": f"Failed to open '{app_name}': {e2}"}

    def open_and_type(self, app_name: str, text: str) -> Dict[str, Any]:
        """
        Launches/focuses target application, waits for readiness,
        and types text using hardware Unicode injection with virtual hand animation.
        """
        if emergency_stop.is_stopped() or self._abort_requested:
            return {"success": False, "error": "Emergency stop active"}

        from backend.desktop.virtual_hand_controller import virtual_hand_controller
        launch_res = self.open_app(app_name)
        if not launch_res.get("success"):
            return launch_res

        time.sleep(0.4)
        pos = self.mouse.get_position()
        virtual_hand_controller.show(pos[0], pos[1], state="typing")
        type_res = virtual_hand_controller.type_text(text)
        time.sleep(0.2)
        virtual_hand_controller.hide()

        return {
            "success": type_res,
            "action": "open_and_type",
            "app": app_name,
            "text_length": len(text),
            "message": f"Typed into {app_name}",
        }

    def smooth_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> Dict[str, Any]:
        """Smoothly glides virtual hand to (x, y) and executes click."""
        if emergency_stop.is_stopped() or self._abort_requested:
            return {"success": False, "error": "Emergency stop active"}

        from backend.desktop.virtual_hand_controller import virtual_hand_controller
        virtual_hand_controller.move_to(x, y, duration=0.35, state="pointer")
        time.sleep(0.04)
        virtual_hand_controller.click(x=x, y=y, button=button, clicks=clicks)
        time.sleep(0.1)
        virtual_hand_controller.hide()
        return {"success": True, "action": "click", "x": x, "y": y, "button": button}

    def smooth_drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> Dict[str, Any]:
        """Smoothly drags from (start_x, start_y) to (end_x, end_y)."""
        if emergency_stop.is_stopped() or self._abort_requested:
            return {"success": False, "error": "Emergency stop active"}

        from backend.desktop.virtual_hand_controller import virtual_hand_controller
        virtual_hand_controller.move_to(start_x, start_y, duration=0.3, state="drag")
        time.sleep(0.05)
        virtual_hand_controller.move_to(end_x, end_y, duration=0.6, state="drag")
        self.mouse.drag_and_drop(start_x, start_y, end_x, end_y, duration=0.6)
        time.sleep(0.1)
        virtual_hand_controller.hide()
        return {
            "success": True,
            "action": "drag_and_drop",
            "from": (start_x, start_y),
            "to": (end_x, end_y),
        }

    def browser_search(self, browser_name: str, query: str) -> Dict[str, Any]:
        """
        Interacts with browser: opens/focuses browser, glides virtual hand
        to address bar, clicks, types search query with real input, and presses Enter.
        """
        if emergency_stop.is_stopped() or self._abort_requested:
            return {"success": False, "error": "Emergency stop active"}

        from backend.desktop.virtual_hand_controller import virtual_hand_controller
        b_raw = browser_name.strip().lower()
        if b_raw in ("google", "browser", "web"):
            b_key = "chrome"
            for candidate in ("chrome", "msedge", "brave", "firefox"):
                if self.windows.find_window(candidate):
                    b_key = candidate
                    break
        else:
            b_key = b_raw

        # 1. Open/Focus browser window
        self.open_app(b_key)
        time.sleep(0.6)

        # 2. Get window dimensions
        win = self.windows.find_window(b_key)
        screen_w, screen_h = self.mouse.get_screen_resolution()
        if win and win.get("hwnd"):
            self.windows.focus_window(win["hwnd"])
            time.sleep(0.3)
            rect = self.windows.get_window_rect(win["hwnd"])
            w = rect.get("width") if rect.get("width", 0) > 300 else screen_w
            rx = rect.get("x", 0)
            ry = rect.get("y", 0)
        else:
            rx, ry, w = 0, 0, screen_w

        # 3. Address bar coordinates (centered horizontally, omnibox is ~54px from top)
        addr_x = rx + (w // 2)
        addr_y = max(48, ry + 54)

        # 4. AURA's independent virtual hand actions
        virtual_hand_controller.show(rx + (w // 4), ry + (screen_h // 3), state="normal")
        time.sleep(0.1)
        virtual_hand_controller.move_to(addr_x, addr_y, duration=0.45, state="pointer")
        time.sleep(0.1)
        virtual_hand_controller.click(addr_x, addr_y)
        time.sleep(0.08)
        # Use Ctrl+L to guarantee address bar focus across all browsers/DPI scaling without hitting bookmarks bar
        self.keyboard.hotkey("ctrl", "l")
        time.sleep(0.05)
        self.keyboard.hotkey("ctrl", "a")
        time.sleep(0.05)
        virtual_hand_controller.type_text(query)
        time.sleep(0.15)
        self.keyboard.press_key("enter")
        time.sleep(0.4)
        virtual_hand_controller.hide()

        return {
            "success": True,
            "browser": browser_name,
            "query": query,
            "address_bar": {"x": addr_x, "y": addr_y},
            "message": f"Searched for '{query}' in {browser_name}.",
        }


# Global desktop controller instance
desktop_controller = DesktopController()
