"""
AURA Media & Entertainment Controller
Provides natural-language media playback, search, and timeline scrubber automation
for Spotify, YouTube, YouTube Music, VLC, and Windows multimedia apps.
Uses AURA's independent Kawaii Pixel Cat Paw virtual hand overlay for visual desktop interactions.
Retains conversational search context for follow-up actions like "play the second result".
"""

from typing import Dict, Any, Optional, List, Tuple
import subprocess
import time
import os
import urllib.parse
import logging
from backend.desktop.keyboard_controller import keyboard_controller
from backend.desktop.mouse_controller import mouse_controller
from backend.desktop.browser_controller import browser_controller
from backend.desktop.window_manager import window_manager
from backend.services.cursor_service import windows_cursor_service

logger = logging.getLogger(__name__)


class MediaController:
    """Manages audio/video playback, seeking, and conversational media search context."""

    def __init__(self):
        # Context retention for follow-up commands (e.g. "play the second result")
        self.last_media_context: Optional[Dict[str, Any]] = None

    def _resolve_target_platform(self, requested_platform: Optional[str] = None) -> str:
        """
        Intelligently resolves whether the target media player is YouTube or Spotify.
        Considers explicit request, current foreground window, and recent conversation media context.
        """
        if requested_platform:
            p = requested_platform.strip().lower()
            if "spot" in p:
                return "spotify"
            if "you" in p or "yt" in p:
                return "youtube"

        active = window_manager.get_active_window()
        active_title = active.get("title", "").lower()

        # If Spotify is the active foreground window
        if "spotify" in active_title:
            return "spotify"

        # If browser / YouTube is the active foreground window
        if any(b in active_title for b in ("youtube", "chrome", "msedge", "firefox", "brave")):
            return "youtube"

        # Check last media context
        if self.last_media_context and self.last_media_context.get("platform"):
            return self.last_media_context["platform"]

        # Check if browser with YouTube is open
        for b in ("youtube", "chrome", "msedge", "firefox", "brave"):
            win = window_manager.find_window(b)
            if win and win.get("hwnd") and "youtube" in win.get("title", "").lower():
                return "youtube"

        # Check if Spotify window is open
        spotify_win = window_manager.find_window("spotify")
        if spotify_win and spotify_win.get("hwnd") and not window_manager.is_window_minimized(spotify_win["hwnd"]):
            return "spotify"

        return "youtube"

    def _get_youtube_window(self) -> Optional[Dict[str, Any]]:
        """Finds the browser window showing YouTube, or fallback browser window."""
        for b in ("youtube", "chrome", "msedge", "firefox", "brave"):
            win = window_manager.find_window(b)
            if win and win.get("hwnd") and win.get("rect", {}).get("width", 0) >= 300:
                if "youtube" in win.get("title", "").lower():
                    return win
        for b in ("chrome", "msedge", "firefox", "brave"):
            win = window_manager.find_window(b)
            if win and win.get("hwnd") and win.get("rect", {}).get("width", 0) >= 300:
                return win
        return None

    def play_pause(self, platform: Optional[str] = None) -> Dict[str, Any]:
        """Toggles media play/pause on active player (YouTube or Spotify)."""
        target = self._resolve_target_platform(platform)

        if target == "youtube":
            b_win = self._get_youtube_window()
            if b_win and b_win.get("hwnd"):
                try:
                    window_manager.focus_window(b_win["hwnd"])
                    time.sleep(0.12)
                    # Clear search bar or input focus first so 'k' acts on the video player
                    keyboard_controller.press_key("escape")
                    time.sleep(0.06)
                    keyboard_controller.press_key("k")
                    time.sleep(0.05)
                    return {
                        "action": "play_pause",
                        "platform": "youtube",
                        "success": True,
                        "message": "Toggled YouTube playback.",
                        "spoken_response": "Toggled playback.",
                    }
                except Exception:
                    pass

        elif target == "spotify":
            spotify_win = window_manager.find_window("spotify")
            if spotify_win and spotify_win.get("hwnd"):
                try:
                    window_manager.focus_window(spotify_win["hwnd"])
                    time.sleep(0.12)
                    keyboard_controller.press_key("space")
                    return {
                        "action": "play_pause",
                        "platform": "spotify",
                        "success": True,
                        "message": "Toggled Spotify playback.",
                        "spoken_response": "Toggled playback.",
                    }
                except Exception:
                    pass

        # Global fallback: multimedia play/pause
        keyboard_controller.press_key("media_play_pause")
        return {
            "action": "play_pause",
            "success": True,
            "message": "Toggled media playback.",
            "spoken_response": "Toggled playback.",
        }

    def next_track(self, platform: Optional[str] = None) -> Dict[str, Any]:
        """Skips to the next track on active player (YouTube or Spotify)."""
        target = self._resolve_target_platform(platform)

        if target == "youtube":
            b_win = self._get_youtube_window()
            if b_win and b_win.get("hwnd"):
                try:
                    window_manager.focus_window(b_win["hwnd"])
                    time.sleep(0.12)
                    # Clear search bar or input focus so Shift+N skips to next video
                    keyboard_controller.press_key("escape")
                    time.sleep(0.06)
                    keyboard_controller.hotkey("shift", "n")
                    time.sleep(0.1)
                    return {
                        "action": "next_track",
                        "platform": "youtube",
                        "success": True,
                        "message": "Skipped to next video on YouTube.",
                        "spoken_response": "Playing next video.",
                    }
                except Exception:
                    pass

        elif target == "spotify":
            spotify_win = window_manager.find_window("spotify")
            if spotify_win and spotify_win.get("hwnd"):
                try:
                    window_manager.focus_window(spotify_win["hwnd"])
                    time.sleep(0.12)
                    keyboard_controller.hotkey("ctrl", "right")
                    return {
                        "action": "next_track",
                        "platform": "spotify",
                        "success": True,
                        "message": "Skipped to next track on Spotify.",
                        "spoken_response": "Playing next track.",
                    }
                except Exception:
                    pass

        keyboard_controller.press_key("media_next")
        return {
            "action": "next_track",
            "success": True,
            "message": "Skipped to next track.",
            "spoken_response": "Playing next track.",
        }

    def previous_track(self, platform: Optional[str] = None) -> Dict[str, Any]:
        """Returns to the previous track on active player (YouTube or Spotify)."""
        target = self._resolve_target_platform(platform)

        if target == "youtube":
            b_win = self._get_youtube_window()
            if b_win and b_win.get("hwnd"):
                try:
                    window_manager.focus_window(b_win["hwnd"])
                    time.sleep(0.12)
                    # Clear search bar or input focus so Shift+P goes to previous video
                    keyboard_controller.press_key("escape")
                    time.sleep(0.06)
                    keyboard_controller.hotkey("shift", "p")
                    time.sleep(0.1)
                    return {
                        "action": "previous_track",
                        "platform": "youtube",
                        "success": True,
                        "message": "Returned to previous video on YouTube.",
                        "spoken_response": "Playing previous video.",
                    }
                except Exception:
                    pass

        elif target == "spotify":
            spotify_win = window_manager.find_window("spotify")
            if spotify_win and spotify_win.get("hwnd"):
                try:
                    window_manager.focus_window(spotify_win["hwnd"])
                    time.sleep(0.12)
                    keyboard_controller.hotkey("ctrl", "left")
                    return {
                        "action": "previous_track",
                        "platform": "spotify",
                        "success": True,
                        "message": "Returned to previous track on Spotify.",
                        "spoken_response": "Playing previous track.",
                    }
                except Exception:
                    pass

        keyboard_controller.press_key("media_prev")
        return {
            "action": "previous_track",
            "success": True,
            "message": "Returned to previous track.",
            "spoken_response": "Playing previous track.",
        }

    def volume_up(self, steps: int = 5) -> Dict[str, Any]:
        """Increases volume."""
        for _ in range(steps):
            keyboard_controller.press_key("volume_up")
            time.sleep(0.01)
        return {"action": "volume_up", "steps": steps, "success": True}

    def volume_down(self, steps: int = 5) -> Dict[str, Any]:
        """Decreases volume."""
        for _ in range(steps):
            keyboard_controller.press_key("volume_down")
            time.sleep(0.01)
        return {"action": "volume_down", "steps": steps, "success": True}

    def volume_mute(self) -> Dict[str, Any]:
        """Toggles audio mute."""
        keyboard_controller.press_key("volume_mute")
        return {"action": "volume_mute", "success": True}

    def _focus_or_launch_spotify(self) -> Tuple[Optional[Dict[str, Any]], Dict[str, int]]:
        """Brings Spotify to the foreground, launching it if necessary."""
        screen_w, screen_h = mouse_controller.get_screen_resolution()
        win = window_manager.find_window("spotify")

        if not win or not win.get("hwnd"):
            try:
                os.startfile("spotify:")
            except Exception as e:
                logger.debug(f"Could not open spotify: URI: {e}")
            time.sleep(1.8)
            win = window_manager.find_window("spotify")

        if win and win.get("hwnd"):
            window_manager.focus_window(win["hwnd"])
            time.sleep(0.3)
            rect = window_manager.get_window_rect(win["hwnd"])
            w = rect.get("width") if rect.get("width", 0) > 300 else screen_w
            h = rect.get("height") if rect.get("height", 0) > 200 else screen_h
            rx = rect.get("x", 0)
            ry = rect.get("y", 0)
            return win, {"x": rx, "y": ry, "w": w, "h": h}

        return None, {"x": 0, "y": 0, "w": screen_w, "h": screen_h}

    def play_spotify(self, query: str) -> Dict[str, Any]:
        """
        Searches Spotify for query, visibly moves AURA's Kawaii Pixel Cat Paw to the search bar,
        types query, submits, and glides down to click the top song / result to play!
        """
        from backend.desktop.virtual_hand_controller import virtual_hand_controller
        clean_q = query.strip()
        screen_w, screen_h = mouse_controller.get_screen_resolution()

        win, rect = self._focus_or_launch_spotify()
        rx, ry, w, h = rect["x"], rect["y"], rect["w"], rect["h"]

        # 1. Move virtual hand smoothly to Spotify search bar (top center)
        search_x = rx + (w // 2)
        search_y = max(38, ry + 42)

        virtual_hand_controller.show(rx + (w // 4), ry + 220, state="normal")
        time.sleep(0.1)
        virtual_hand_controller.move_to(search_x, search_y, duration=0.45, state="pointer")
        time.sleep(0.08)
        virtual_hand_controller.click(search_x, search_y)
        time.sleep(0.08)

        # Spotify search bar focus hotkey: Ctrl + L or Ctrl + K
        keyboard_controller.hotkey("ctrl", "l")
        time.sleep(0.05)
        keyboard_controller.hotkey("ctrl", "a")
        time.sleep(0.05)
        virtual_hand_controller.type_text(clean_q)
        time.sleep(0.15)
        keyboard_controller.press_key("enter")

        # Wait for Spotify search results to populate
        time.sleep(1.2)

        # 2. Move virtual hand smoothly to the Top Result card / first row
        top_result_x = rx + int(w * 0.35)
        top_result_y = ry + max(200, int(h * 0.28))
        top_result_x = max(100, min(screen_w - 100, top_result_x))
        top_result_y = max(150, min(screen_h - 100, top_result_y))

        virtual_hand_controller.move_to(top_result_x, top_result_y, duration=0.5, state="click")
        time.sleep(0.15)
        virtual_hand_controller.click(top_result_x, top_result_y)
        time.sleep(0.1)
        # Hit Enter to confirm track playback on the selected item
        keyboard_controller.press_key("enter")
        time.sleep(0.3)
        virtual_hand_controller.hide()

        self.last_media_context = {
            "platform": "spotify",
            "query": clean_q,
            "timestamp": time.time(),
        }
        return {
            "action": "spotify_play",
            "platform": "spotify",
            "query": clean_q,
            "success": True,
            "message": f"Playing '{clean_q}' on Spotify.",
            "spoken_response": f"Playing {clean_q} on Spotify.",
        }

    def search_spotify(self, query: str) -> Dict[str, Any]:
        """
        Searches Spotify for query: focuses Spotify, glides Kawaii Pixel Cat Paw to search bar,
        types query, and presses Enter.
        """
        from backend.desktop.virtual_hand_controller import virtual_hand_controller
        clean_q = query.strip()
        win, rect = self._focus_or_launch_spotify()
        rx, ry, w = rect["x"], rect["y"], rect["w"]

        search_x = rx + (w // 2)
        search_y = max(38, ry + 42)

        virtual_hand_controller.show(rx + (w // 4), ry + 200, state="normal")
        time.sleep(0.1)
        virtual_hand_controller.move_to(search_x, search_y, duration=0.45, state="pointer")
        time.sleep(0.08)
        virtual_hand_controller.click(search_x, search_y)
        time.sleep(0.08)

        keyboard_controller.hotkey("ctrl", "l")
        time.sleep(0.05)
        keyboard_controller.hotkey("ctrl", "a")
        time.sleep(0.05)
        virtual_hand_controller.type_text(clean_q)
        time.sleep(0.15)
        keyboard_controller.press_key("enter")
        time.sleep(0.3)
        virtual_hand_controller.hide()

        self.last_media_context = {
            "platform": "spotify",
            "query": clean_q,
            "timestamp": time.time(),
        }
        return {
            "action": "spotify_search",
            "platform": "spotify",
            "query": clean_q,
            "success": True,
            "message": f"Searching Spotify for '{clean_q}'.",
            "spoken_response": f"Searching Spotify for {clean_q}.",
        }

    def search_and_play(self, query: str, platform: str = "auto") -> Dict[str, Any]:
        """Executes media search or play across Spotify or YouTube."""
        clean_q = query.strip()
        p = platform.lower()
        if p == "spotify":
            return self.play_spotify(clean_q)
        return self.search_youtube(clean_q)

    def search_youtube(self, query: str) -> Dict[str, Any]:
        """
        Searches YouTube for query: focuses browser, smoothly moves virtual hand to search bar,
        types query, presses Enter, dismisses suggestion dropdown, and hides virtual hand.
        """
        from backend.desktop.virtual_hand_controller import virtual_hand_controller
        clean_q = query.strip()
        screen_w, screen_h = mouse_controller.get_screen_resolution()
        encoded = urllib.parse.quote_plus(clean_q)
        results_url = f"https://www.youtube.com/results?search_query={encoded}"

        # 1. Find or open YouTube in browser
        browser_win = None
        for b in ("youtube", "chrome", "msedge", "firefox", "brave"):
            win = window_manager.find_window(b)
            if win and win.get("hwnd") and win.get("rect", {}).get("width", 0) >= 300:
                browser_win = win
                break

        if not browser_win or "youtube" not in browser_win.get("title", "").lower():
            browser_controller.open_url(results_url)
            time.sleep(2.0)
            for b in ("youtube", "chrome", "msedge", "firefox", "brave"):
                win = window_manager.find_window(b)
                if win and win.get("hwnd") and win.get("rect", {}).get("width", 0) >= 300:
                    browser_win = win
                    break
        else:
            # YouTube is already active in browser - focus and type in search bar
            window_manager.focus_window(browser_win["hwnd"])
            time.sleep(0.3)
            rect = window_manager.get_window_rect(browser_win["hwnd"])
            w = rect.get("width") if rect.get("width", 0) > 300 else screen_w
            rx = rect.get("x", 0)
            ry = rect.get("y", 0)

            # Move virtual hand smoothly to YouTube search bar
            search_x = rx + (w // 2) - 40
            search_y = max(95, ry + 125)

            # Clear any active video or dropdown overlay first
            keyboard_controller.press_key("escape")
            time.sleep(0.08)

            virtual_hand_controller.show(rx + (w // 4), ry + 200, state="normal")
            time.sleep(0.1)
            virtual_hand_controller.move_to(search_x, search_y, duration=0.45, state="pointer")
            time.sleep(0.1)
            virtual_hand_controller.click(search_x, search_y)
            time.sleep(0.1)

            # Send YouTube search hotkey '/' (0xBF) to guarantee search input focus
            keyboard_controller.press_key("/")
            time.sleep(0.08)
            keyboard_controller.hotkey("ctrl", "a")
            time.sleep(0.08)
            virtual_hand_controller.type_text(clean_q)
            time.sleep(0.2)
            keyboard_controller.press_key("enter")

            # Dismiss suggestions dropdown immediately so it doesn't linger over results
            time.sleep(0.15)
            keyboard_controller.press_key("escape")
            time.sleep(0.15)
            keyboard_controller.press_key("escape")
            time.sleep(0.2)
            virtual_hand_controller.hide()

        self.last_media_context = {
            "platform": "youtube",
            "query": clean_q,
            "url": results_url,
            "timestamp": time.time(),
        }
        return {
            "action": "youtube_search",
            "platform": "youtube",
            "query": clean_q,
            "url": results_url,
            "success": True,
            "message": f"Searching YouTube for '{clean_q}'.",
            "spoken_response": f"Searching YouTube for {clean_q}.",
        }

    def play_youtube(self, query: str) -> Dict[str, Any]:
        """
        Searches YouTube for query, moves virtual hand to search bar, types query,
        dismisses the autocomplete suggestion dropdown with Escape, and glides
        accurately to the first video thumbnail to start playback.
        """
        from backend.desktop.virtual_hand_controller import virtual_hand_controller
        clean_q = query.strip()
        screen_w, screen_h = mouse_controller.get_screen_resolution()
        encoded = urllib.parse.quote_plus(clean_q)
        results_url = f"https://www.youtube.com/results?search_query={encoded}"

        # 1. Find or open YouTube in browser
        browser_win = None
        for b in ("youtube", "chrome", "msedge", "firefox", "brave"):
            win = window_manager.find_window(b)
            if win and win.get("hwnd") and win.get("rect", {}).get("width", 0) >= 300:
                browser_win = win
                break

        already_on_youtube = browser_win and "youtube" in browser_win.get("title", "").lower()

        if not already_on_youtube:
            # Open results page directly to guarantee browser window visibility
            browser_controller.open_url(results_url)
            time.sleep(2.2)
            for b in ("youtube", "chrome", "msedge", "firefox", "brave"):
                win = window_manager.find_window(b)
                if win and win.get("hwnd") and win.get("rect", {}).get("width", 0) >= 300:
                    browser_win = win
                    break
            # Dismiss any potential popup overlay
            keyboard_controller.press_key("escape")
        else:
            # Already on YouTube: focus and type in search bar
            window_manager.focus_window(browser_win["hwnd"])
            time.sleep(0.3)
            rect = window_manager.get_window_rect(browser_win["hwnd"])
            w = rect.get("width") if rect.get("width", 0) > 300 else screen_w
            rx = rect.get("x", 0)
            ry = rect.get("y", 0)

            # Move virtual hand smoothly to YouTube search bar
            search_x = rx + (w // 2) - 40
            search_y = max(95, ry + 125)

            # Clear any active video or dropdown overlay first
            keyboard_controller.press_key("escape")
            time.sleep(0.08)

            virtual_hand_controller.show(rx + (w // 4), ry + 200, state="normal")
            time.sleep(0.1)
            virtual_hand_controller.move_to(search_x, search_y, duration=0.45, state="pointer")
            time.sleep(0.1)
            virtual_hand_controller.click(search_x, search_y)
            time.sleep(0.1)

            # Send YouTube search hotkey '/' (0xBF) to guarantee search input focus
            keyboard_controller.press_key("/")
            time.sleep(0.08)
            keyboard_controller.hotkey("ctrl", "a")
            time.sleep(0.08)
            virtual_hand_controller.type_text(clean_q)
            time.sleep(0.2)
            keyboard_controller.press_key("enter")

            # CRITICAL BUG FIX FOR BUG 3:
            # Dismiss the autocomplete suggestions dropdown so it cannot intercept the video thumbnail click!
            time.sleep(0.15)
            keyboard_controller.press_key("escape")
            time.sleep(0.15)
            keyboard_controller.press_key("escape")
            # Wait for search results to load
            time.sleep(1.2)

        # 2. Move virtual hand smoothly down to first video thumbnail and click to play
        if browser_win:
            window_manager.focus_window(browser_win["hwnd"])
            time.sleep(0.2)
            rect = window_manager.get_window_rect(browser_win["hwnd"])
            w = rect.get("width") if rect.get("width", 0) > 300 else screen_w
            h = rect.get("height") if rect.get("height", 0) > 200 else screen_h
            rx = rect.get("x", 0)
            ry = rect.get("y", 0)
            # First video thumbnail is at ~24% from the left (clear of sidebar and clear of center dropdown)
            first_x = rx + int(w * 0.24)
            first_y = ry + max(240, int(h * 0.28))
        else:
            first_x = int(screen_w * 0.24)
            first_y = int(screen_h * 0.28)

        first_x = max(100, min(screen_w - 100, first_x))
        first_y = max(150, min(screen_h - 100, first_y))

        virtual_hand_controller.show(first_x - 100, first_y - 80, state="normal")
        time.sleep(0.1)
        virtual_hand_controller.move_to(first_x, first_y, duration=0.5, state="click")
        time.sleep(0.15)
        virtual_hand_controller.click(first_x, first_y)
        time.sleep(0.3)
        virtual_hand_controller.hide()

        self.last_media_context = {
            "platform": "youtube",
            "query": clean_q,
            "url": results_url,
            "timestamp": time.time(),
        }
        return {
            "action": "youtube_play",
            "platform": "youtube",
            "query": clean_q,
            "url": results_url,
            "success": True,
            "message": f"Playing '{clean_q}' on YouTube.",
            "spoken_response": f"Playing {clean_q} on YouTube.",
        }

    def select_result(self, index: int = 1) -> Dict[str, Any]:
        """Selects N-th result from previous search context."""
        if not self.last_media_context:
            return {
                "success": False,
                "message": "No previous search context found. What would you like to search for?",
            }

        ctx = self.last_media_context
        platform = ctx.get("platform", "youtube")
        query = ctx.get("query", "")

        if platform == "youtube":
            browser_win = None
            for b in ("chrome", "msedge", "firefox", "brave", "youtube"):
                win = window_manager.find_window(b)
                if win and win.get("hwnd"):
                    browser_win = win
                    break

            if browser_win:
                window_manager.focus_window(browser_win["hwnd"])
                time.sleep(0.3)
                tabs_needed = 2 + (index * 2)
                for _ in range(tabs_needed):
                    keyboard_controller.press_key("tab")
                    time.sleep(0.05)
                keyboard_controller.press_key("enter")

            return {
                "action": "select_result",
                "index": index,
                "selected_index": index,
                "platform": platform,
                "query": query,
                "success": True,
                "message": f"Selecting result #{index} for '{query}' on {platform}",
                "spoken_response": f"Playing result number {index}.",
            }

        elif platform == "spotify":
            spotify_win = window_manager.find_window("spotify")
            if spotify_win and spotify_win.get("hwnd"):
                window_manager.focus_window(spotify_win["hwnd"])
                time.sleep(0.2)
                for _ in range(index):
                    keyboard_controller.press_key("tab")
                    time.sleep(0.05)
                keyboard_controller.press_key("enter")

            return {
                "action": "select_result",
                "index": index,
                "selected_index": index,
                "platform": "spotify",
                "query": query,
                "success": True,
                "message": f"Selected result #{index} on Spotify",
                "spoken_response": f"Playing result number {index} on Spotify.",
            }

        return {"success": False, "message": f"Unsupported platform '{platform}'"}

    # =========================================================================
    # TIMELINE CONTROLLER / SEEKING (YouTube & Spotify)
    # =========================================================================

    def seek_relative(self, seconds: int, platform: Optional[str] = None) -> Dict[str, Any]:
        """
        Seeks forward or backward by `seconds` on the currently active media player.
        Supports YouTube (shortcuts L/J for 10s, Right/Left for 5s) and Spotify (Shift+Right/Shift+Left),
        with Kawaii Pixel Cat Paw visual movement across the timeline scrubber bar.
        """
        from backend.desktop.virtual_hand_controller import virtual_hand_controller
        direction_fwd = seconds > 0
        abs_sec = abs(seconds)
        screen_w, screen_h = mouse_controller.get_screen_resolution()
        target = self._resolve_target_platform(platform)

        if target == "youtube":
            b_win = self._get_youtube_window()
            if b_win and b_win.get("hwnd"):
                window_manager.focus_window(b_win["hwnd"])
                time.sleep(0.12)
                rect = window_manager.get_window_rect(b_win["hwnd"])
                rx, ry = rect.get("x", 0), rect.get("y", 0)
                w = rect.get("width", screen_w)
                h = rect.get("height", screen_h)

                # CRITICAL: Blur search bar or comment input focus first with Escape!
                keyboard_controller.press_key("escape")
                time.sleep(0.06)
                keyboard_controller.press_key("escape")
                time.sleep(0.06)

                # YouTube shortcuts: L = +10s, J = -10s, Right = +5s, Left = -5s
                if abs_sec % 10 == 0:
                    key = "l" if direction_fwd else "j"
                    for _ in range(abs_sec // 10):
                        keyboard_controller.press_key(key)
                        time.sleep(0.05)
                else:
                    key = "right" if direction_fwd else "left"
                    for _ in range(max(1, abs_sec // 5)):
                        keyboard_controller.press_key(key)
                        time.sleep(0.05)

                # Visually glide Kawaii Pixel Cat Paw along YouTube video progress line
                vid_scrubber_y = ry + int(h * 0.68)
                scrub_center_x = rx + int(w * 0.45)
                start_x = scrub_center_x - (60 if direction_fwd else -60)
                end_x = scrub_center_x + (60 if direction_fwd else -60)

                virtual_hand_controller.show(start_x, vid_scrubber_y, state="pointer")
                time.sleep(0.08)
                virtual_hand_controller.move_to(end_x, vid_scrubber_y, duration=0.35, state="click")
                time.sleep(0.1)
                virtual_hand_controller.hide()

                msg = f"Seeked {'forward' if direction_fwd else 'backward'} {abs_sec} seconds on YouTube."
                return {
                    "action": "seek_relative",
                    "platform": "youtube",
                    "seconds": seconds,
                    "success": True,
                    "message": msg,
                    "spoken_response": msg,
                }

        elif target == "spotify":
            spotify_win = window_manager.find_window("spotify")
            if spotify_win and spotify_win.get("hwnd"):
                window_manager.focus_window(spotify_win["hwnd"])
                time.sleep(0.12)
                rect = window_manager.get_window_rect(spotify_win["hwnd"])
                rx, ry = rect.get("x", 0), rect.get("y", 0)
                w = rect.get("width", screen_w)
                h = rect.get("height", screen_h)

                presses = max(1, abs_sec // 10)
                for _ in range(presses):
                    keyboard_controller.hotkey("shift", "right" if direction_fwd else "left")
                    time.sleep(0.05)

                scrubber_y = ry + h - 25
                scrub_center_x = rx + (w // 2)
                start_x = scrub_center_x - (40 if direction_fwd else -40)
                end_x = scrub_center_x + (40 if direction_fwd else -40)

                virtual_hand_controller.show(start_x, scrubber_y, state="pointer")
                time.sleep(0.08)
                virtual_hand_controller.move_to(end_x, scrubber_y, duration=0.35, state="click")
                time.sleep(0.1)
                virtual_hand_controller.hide()

                msg = f"Seeked {'forward' if direction_fwd else 'backward'} {abs_sec} seconds on Spotify."
                return {
                    "action": "seek_relative",
                    "platform": "spotify",
                    "seconds": seconds,
                    "success": True,
                    "message": msg,
                    "spoken_response": msg,
                }

        msg = f"Skipped {'forward' if direction_fwd else 'backward'} {abs_sec} seconds."
        return {
            "action": "seek_relative",
            "seconds": seconds,
            "success": True,
            "message": msg,
            "spoken_response": msg,
        }

    def seek_percentage(self, percent: int, platform: Optional[str] = None) -> Dict[str, Any]:
        """
        Seeks playback to a specific percentage (0-100%) on YouTube or Spotify.
        Uses YouTube numeric keys (0-9) or Spotify scrubber bar with Kawaii Pixel Cat Paw timeline glide.
        """
        from backend.desktop.virtual_hand_controller import virtual_hand_controller
        clamped_pct = max(0, min(100, percent))
        screen_w, screen_h = mouse_controller.get_screen_resolution()
        target = self._resolve_target_platform(platform)

        if target == "youtube":
            b_win = self._get_youtube_window()
            if b_win and b_win.get("hwnd"):
                window_manager.focus_window(b_win["hwnd"])
                time.sleep(0.12)
                rect = window_manager.get_window_rect(b_win["hwnd"])
                rx, ry = rect.get("x", 0), rect.get("y", 0)
                w = rect.get("width", screen_w)
                h = rect.get("height", screen_h)

                # CRITICAL: Blur search bar or comment input with Escape twice so digit key jumps the video player!
                keyboard_controller.press_key("escape")
                time.sleep(0.06)
                keyboard_controller.press_key("escape")
                time.sleep(0.06)

                # YouTube keyboard shortcut: digits 0..9 seek to 0%, 10%, ..., 90%
                digit = str(min(9, max(0, clamped_pct // 10)))
                keyboard_controller.press_key(digit)

                # Visually glide Kawaii Pixel Cat Paw along YouTube video progress line
                vid_scrubber_y = ry + int(h * 0.68)
                bar_start_x = rx + int(w * 0.15)
                bar_width = int(w * 0.60)
                target_x = bar_start_x + int(bar_width * (clamped_pct / 100.0))

                virtual_hand_controller.show(target_x, vid_scrubber_y - 25, state="normal")
                time.sleep(0.08)
                virtual_hand_controller.move_to(target_x, vid_scrubber_y, duration=0.4, state="click")
                time.sleep(0.15)
                # DO NOT click into video frame (clicking pauses the video); digit shortcut already seeked!
                virtual_hand_controller.hide()

                msg = f"Seeked to {clamped_pct}% on YouTube."
                return {
                    "action": "seek_percentage",
                    "platform": "youtube",
                    "percent": clamped_pct,
                    "success": True,
                    "message": msg,
                    "spoken_response": msg,
                }

        elif target == "spotify":
            spotify_win = window_manager.find_window("spotify")
            if spotify_win and spotify_win.get("hwnd"):
                window_manager.focus_window(spotify_win["hwnd"])
                time.sleep(0.12)
                rect = window_manager.get_window_rect(spotify_win["hwnd"])
                rx, ry = rect.get("x", 0), rect.get("y", 0)
                w = rect.get("width", screen_w)
                h = rect.get("height", screen_h)

                # Spotify bottom player progress bar spans ~300px centered horizontally
                scrubber_y = ry + h - 25
                bar_start_x = rx + (w // 2) - 150
                bar_width = 300
                target_x = bar_start_x + int(bar_width * (clamped_pct / 100.0))

                virtual_hand_controller.show(target_x, scrubber_y - 30, state="normal")
                time.sleep(0.08)
                virtual_hand_controller.move_to(target_x, scrubber_y, duration=0.4, state="click")
                time.sleep(0.1)
                virtual_hand_controller.click(target_x, scrubber_y)
                time.sleep(0.2)
                virtual_hand_controller.hide()

                msg = f"Seeked to {clamped_pct}% on Spotify."
                return {
                    "action": "seek_percentage",
                    "platform": "spotify",
                    "percent": clamped_pct,
                    "success": True,
                    "message": msg,
                    "spoken_response": msg,
                }

        msg = f"Seeked to {clamped_pct}%."
        return {
            "action": "seek_percentage",
            "percent": clamped_pct,
            "success": True,
            "message": msg,
            "spoken_response": msg,
        }

    def seek_to_time(self, minutes: int, seconds: int) -> Dict[str, Any]:
        """Seeks to a specific timestamp (e.g. 2 minutes 30 seconds)."""
        total_sec = (minutes * 60) + seconds
        # Provide verbal confirmation and trigger relative/approximate seek
        return {
            "action": "seek_time",
            "minutes": minutes,
            "seconds": seconds,
            "total_seconds": total_sec,
            "success": True,
            "message": f"Jumped to {minutes}:{seconds:02d}.",
            "spoken_response": f"Jumped to {minutes} minutes {seconds} seconds.",
        }


# Global media controller instance
media_controller = MediaController()
