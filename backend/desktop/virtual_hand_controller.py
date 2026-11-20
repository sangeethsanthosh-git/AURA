"""
AURA Independent Virtual Assistant Hand Controller
Coordinates AURA's visual desktop assistant hand (Kawaii Pixel Cat Paw)
with real Windows mouse and keyboard input.
Broadcasts real-time trajectory, click, typing, and state events to the
transparent desktop overlay window via WebSockets.
Includes manual override safety: cancels / yields if the user physically moves the mouse.
Does NOT modify Windows cursor registry or user's system cursor.
"""

import time
import math
import asyncio
import logging
from typing import Dict, Any, Optional, Set, Tuple
from backend.services.virtual_hand_theme_service import virtual_hand_theme_service
from backend.desktop.mouse_controller import mouse_controller
from backend.desktop.keyboard_controller import keyboard_controller

logger = logging.getLogger(__name__)


class VirtualHandController:
    """Controls AURA's independent virtual hand overlay and coordinates desktop input."""

    def __init__(self):
        self.is_active: bool = False
        self.current_x: int = 100
        self.current_y: int = 100
        self.current_state: str = "normal"  # normal, pointer, click, typing, waiting, drag
        self.active_subscribers: Set[Any] = set()
        self._manual_override_threshold: int = 40  # pixels
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def register_subscriber(self, ws: Any) -> None:
        """Registers a WebSocket subscriber (Electron overlay window)."""
        self.active_subscribers.add(ws)
        logger.info(f"VirtualHand subscriber connected. Total: {len(self.active_subscribers)}")

    def unregister_subscriber(self, ws: Any) -> None:
        """Removes a WebSocket subscriber."""
        self.active_subscribers.discard(ws)
        logger.info(f"VirtualHand subscriber disconnected. Total: {len(self.active_subscribers)}")

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Captures running asyncio loop for threadsafe event emission."""
        self._loop = loop

    def broadcast(self, payload: Dict[str, Any]) -> None:
        """Broadcasts event payload to all connected overlay windows."""
        if not self.active_subscribers:
            return

        dead_sockets = set()
        for ws in list(self.active_subscribers):
            try:
                if self._loop and self._loop.is_running():
                    asyncio.run_coroutine_threadsafe(ws.send_json(payload), self._loop)
                else:
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(ws.send_json(payload))
                    except RuntimeError:
                        res = ws.send_json(payload)
                        if asyncio.iscoroutine(res):
                            asyncio.run(res)
            except Exception:
                dead_sockets.add(ws)

        for ws in dead_sockets:
            self.active_subscribers.discard(ws)

    def check_manual_user_override(self, initial_pos: Tuple[int, int]) -> bool:
        """
        Detects if the user physically moved the mouse during automation.
        If displaced by > threshold pixels, triggers safety override.
        """
        cur_x, cur_y = mouse_controller.get_position()
        dist = math.hypot(cur_x - initial_pos[0], cur_y - initial_pos[1])
        if dist > self._manual_override_threshold:
            logger.warning(f"Manual user mouse override detected (dist={dist:.1f}px). Yielding control.")
            self.hide()
            return True
        return False

    def show(self, x: Optional[int] = None, y: Optional[int] = None, state: str = "normal") -> None:
        """Shows AURA's virtual hand at the specified coordinate."""
        theme = virtual_hand_theme_service.get_active_theme()
        if x is None or y is None:
            x, y = mouse_controller.get_position()

        self.is_active = True
        self.current_x = int(x)
        self.current_y = int(y)
        self.current_state = state

        payload = {
            "type": "hand_show",
            "x": self.current_x,
            "y": self.current_y,
            "state": state,
            "theme": theme,
            "timestamp": time.time(),
        }
        self.broadcast(payload)

    def move_to(
        self,
        target_x: int,
        target_y: int,
        duration: float = 0.45,
        state: Optional[str] = None,
        sync_system_mouse: bool = True
    ) -> bool:
        """
        Smoothly glides the virtual hand to (target_x, target_y).
        Optionally synchronizes the Windows system mouse coordinate so clicks land accurately.
        """
        if not self.is_active:
            self.show(self.current_x, self.current_y)

        if state:
            self.current_state = state

        # 1. Broadcast visual move event to overlay window
        payload = {
            "type": "hand_move",
            "from_x": self.current_x,
            "from_y": self.current_y,
            "to_x": int(target_x),
            "to_y": int(target_y),
            "duration": duration,
            "state": self.current_state,
            "timestamp": time.time(),
        }
        self.broadcast(payload)

        # 2. Smoothly coordinate real Windows mouse pointer if needed
        if sync_system_mouse:
            mouse_controller.move_to(target_x, target_y, smooth=True, duration=duration)

        self.current_x = int(target_x)
        self.current_y = int(target_y)
        return True

    def click(
        self,
        target_x: Optional[int] = None,
        target_y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1
    ) -> bool:
        """Visually performs a click with compression & ripple, and executes real input."""
        x = self.current_x if target_x is None else int(target_x)
        y = self.current_y if target_y is None else int(target_y)

        # Broadcast visual click animation
        payload = {
            "type": "hand_click",
            "x": x,
            "y": y,
            "button": button,
            "clicks": clicks,
            "timestamp": time.time(),
        }
        self.broadcast(payload)

        # Real input click
        mouse_controller.click(x, y, button=button, clicks=clicks)
        time.sleep(0.08)
        return True

    def type_text(self, text: str, state: str = "typing") -> bool:
        """Visually animates typing cadence and executes real keyboard input with Virtual Keyboard HUD."""
        payload = {
            "type": "hand_type",
            "text": text,
            "x": self.current_x,
            "y": self.current_y,
            "state": state,
            "timestamp": time.time(),
        }
        self.broadcast(payload)

        # Real input typing with human cadence and zero dropped characters
        keyboard_controller.type_text_safe(text)
        return True

    def set_state(self, state: str) -> None:
        """Switches virtual hand variant (e.g. pointer, typing, waiting, drag)."""
        self.current_state = state
        payload = {
            "type": "hand_state",
            "state": state,
            "x": self.current_x,
            "y": self.current_y,
            "timestamp": time.time(),
        }
        self.broadcast(payload)

    def hide(self) -> None:
        """Fades out and hides AURA's virtual hand overlay."""
        self.is_active = False
        payload = {
            "type": "hand_hide",
            "timestamp": time.time(),
        }
        self.broadcast(payload)


# Global singleton instance
virtual_hand_controller = VirtualHandController()
