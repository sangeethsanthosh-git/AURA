"""
AURA Desktop Perception & UI Element Detector
Provides UI Automation inspection (UIA tree), control detection (buttons, inputs, tabs),
coordinate localization, and action verification.
"""

from typing import List, Dict, Any, Optional, Tuple
import time
import logging
from backend.desktop.window_manager import window_manager

logger = logging.getLogger(__name__)


class DesktopPerception:
    """Discovers UI controls and verifies screen states."""

    def __init__(self):
        self._uia_available = False
        try:
            import pywinauto
            self._pywinauto = pywinauto
            self._uia_available = True
        except ImportError:
            self._pywinauto = None

    def find_control(
        self,
        name_or_query: str,
        window_hwnd: Optional[int] = None,
        control_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Locates a UI control (button, edit, menu, tab) using Windows UI Automation.
        Returns coordinate dictionary with center (x, y) for precise clicking.
        """
        if not self._uia_available:
            return None

        q = name_or_query.strip().lower()

        try:
            from pywinauto import Desktop
            desktop = Desktop(backend="uia")

            # Determine target window or use foreground window
            target_win = None
            if window_hwnd:
                target_win = desktop.window(handle=window_hwnd)
            else:
                fore = window_manager.get_foreground_window()
                if fore.get("hwnd"):
                    target_win = desktop.window(handle=fore["hwnd"])

            if not target_win:
                return None

            # Enumerate descendants
            descendants = target_win.descendants()
            for elem in descendants:
                try:
                    elem_name = (elem.window_text() or "").strip()
                    elem_type = elem.friendly_class_name() or ""

                    if control_type and control_type.lower() not in elem_type.lower():
                        continue

                    if q in elem_name.lower():
                        rect = elem.rectangle()
                        cx = (rect.left + rect.right) // 2
                        cy = (rect.top + rect.bottom) // 2
                        return {
                            "name": elem_name,
                            "type": elem_type,
                            "center": (cx, cy),
                            "rect": {
                                "left": rect.left,
                                "top": rect.top,
                                "right": rect.right,
                                "bottom": rect.bottom,
                                "width": rect.width(),
                                "height": rect.height(),
                            },
                            "is_visible": elem.is_visible(),
                            "is_enabled": elem.is_enabled(),
                        }
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"UIA control search error for '{name_or_query}': {e}")

        return None

    def locate_button(self, name: str, window_hwnd: Optional[int] = None) -> Optional[Tuple[int, int]]:
        """Finds button center coordinate (x, y)."""
        ctrl = self.find_control(name, window_hwnd=window_hwnd, control_type="Button")
        if ctrl and ctrl.get("center"):
            return ctrl["center"]
        # Fallback to any UIA control
        ctrl = self.find_control(name, window_hwnd=window_hwnd)
        if ctrl and ctrl.get("center"):
            return ctrl["center"]
        # Fallback to in-memory OCR text detection
        return self.locate_text_ocr(name, hwnd=window_hwnd)

    def locate_input(self, name_or_placeholder: str, window_hwnd: Optional[int] = None) -> Optional[Tuple[int, int]]:
        """Finds text field or edit box center coordinate (x, y)."""
        ctrl = self.find_control(name_or_placeholder, window_hwnd=window_hwnd, control_type="Edit")
        if ctrl and ctrl.get("center"):
            return ctrl["center"]
        ctrl = self.find_control(name_or_placeholder, window_hwnd=window_hwnd)
        if ctrl and ctrl.get("center"):
            return ctrl["center"]
        return self.locate_text_ocr(name_or_placeholder, hwnd=window_hwnd)

    def locate_text_ocr(self, text: str, hwnd: Optional[int] = None) -> Optional[Tuple[int, int]]:
        """
        Locates screen coordinates (x, y) for arbitrary text/buttons using
        in-memory Windows Media OCR when UIA controls are unavailable or missing.
        """
        try:
            from backend.services.vision_service import VisionService
            from backend.services.ocr_service import ocr_service
            vsvc = VisionService()
            img, _ = vsvc.grab_screen_image()
            target_hwnd = hwnd or (window_manager.get_foreground_window().get("hwnd") or 0)
            coord = ocr_service.find_text_coordinate(text, img, hwnd=target_hwnd)
            img.close()
            del img
            return coord
        except Exception as e:
            logger.debug(f"OCR text location fallback error for '{text}': {e}")
            return None

    def verify_window_opened(self, window_query: str, timeout: float = 4.0) -> bool:
        """Polls until matching window appears and is ready."""
        start = time.perf_counter()
        while time.perf_counter() - start < timeout:
            win = window_manager.find_window(window_query)
            if win and win.get("hwnd"):
                return True
            time.sleep(0.3)
        return False


# Global perception instance
desktop_perception = DesktopPerception()
