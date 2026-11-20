"""
Unit tests for AURA Universal Desktop Mouse, Keyboard, Window, Media, Explorer,
and ActionPlanner desktop automation subsystems.
"""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.desktop import (
    desktop_controller,
    mouse_controller,
    keyboard_controller,
    window_manager,
    desktop_perception,
    browser_controller,
    media_controller,
    file_explorer_controller,
)
from backend.services.tool_registry import tool_registry
from backend.services.action_planner import ActionPlanner
from backend.security.emergency_stop import emergency_stop
from backend.api.app import app


class TestDesktopAutomation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ActionPlanner.initialize_registry()
        cls.client = TestClient(app)

    def setUp(self):
        emergency_stop.reset()
        desktop_controller.reset_abort()

    def test_mouse_monitors_and_resolution(self):
        """Test monitor detection and resolution retrieval."""
        res = mouse_controller.get_screen_resolution()
        self.assertEqual(len(res), 2)
        self.assertGreater(res[0], 0)
        self.assertGreater(res[1], 0)

        monitors = mouse_controller.get_monitors()
        self.assertIsInstance(monitors, list)
        self.assertGreaterEqual(len(monitors), 1)
        self.assertTrue(any(m.get("is_primary") for m in monitors))

    def test_mouse_position_and_bounds(self):
        """Test mouse position retrieval and virtual desktop bounds."""
        x, y = mouse_controller.get_position()
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)

        virtual = mouse_controller.get_virtual_desktop_bounds()
        self.assertIn("width", virtual)
        self.assertIn("height", virtual)
        self.assertGreater(virtual["width"], 0)
        self.assertGreater(virtual["height"], 0)

    def test_mouse_release_all_failsafe(self):
        """Test mouse button release failsafe."""
        res = mouse_controller.release_all()
        self.assertGreaterEqual(res, 0)
        self.assertEqual(len(mouse_controller._held_buttons), 0)

    def test_keyboard_secret_redaction(self):
        """Test keyboard controller types text with secret redaction in logs."""
        with patch("backend.desktop.keyboard_controller.user32.SendInput", return_value=1):
            ok = keyboard_controller.type_text("echo supersecretpass123")
            self.assertTrue(ok)

    def test_keyboard_hotkey_parsing(self):
        """Test keyboard shortcut and modifier resolution."""
        with patch.object(keyboard_controller, "send_key_down", return_value=None):
            with patch.object(keyboard_controller, "send_key_up", return_value=None):
                ok = keyboard_controller.hotkey("ctrl", "shift", "esc")
                self.assertTrue(ok)

    def test_keyboard_release_all_failsafe(self):
        """Test keyboard release all keys failsafe."""
        res = keyboard_controller.release_all()
        self.assertGreaterEqual(res, 0)
        self.assertEqual(len(keyboard_controller._held_keys), 0)

    def test_window_manager_enumeration(self):
        """Test active window and open desktop application enumeration."""
        fore = window_manager.get_foreground_window()
        self.assertIsInstance(fore, dict)
        self.assertIn("hwnd", fore)

        windows = window_manager.list_windows()
        self.assertIsInstance(windows, list)

    def test_desktop_controller_emergency_abort(self):
        """Test emergency abort releases mouse and keyboard inputs instantly."""
        abort_res = desktop_controller.emergency_abort()
        self.assertTrue(abort_res["success"])
        self.assertGreaterEqual(abort_res["mouse_released"], 0)
        self.assertGreaterEqual(abort_res["keys_released"], 0)
        self.assertTrue(desktop_controller._abort_requested)

    def test_media_controller_follow_up_context(self):
        """Test conversational follow-up memory in media controller."""
        # 1. Perform search
        with patch.object(browser_controller, "open_url", return_value={"success": True}):
            search_res = media_controller.search_youtube("lo-fi hip hop")
            self.assertTrue(search_res["success"])
            self.assertIsNotNone(media_controller.last_media_context)
            self.assertEqual(media_controller.last_media_context["query"], "lo-fi hip hop")

        # 2. Select 2nd result via conversational follow-up
        with patch.object(keyboard_controller, "press_key", return_value=True):
            with patch.object(window_manager, "focus_window", return_value=True):
                sel_res = media_controller.select_result(2)
                self.assertTrue(sel_res.get("success"))
                self.assertEqual(sel_res.get("selected_index"), 2)

    def test_file_explorer_controller_common_folders(self):
        """Test file explorer folder query resolution."""
        with patch("subprocess.Popen") as mock_popen:
            res = file_explorer_controller.open_folder("downloads")
            self.assertTrue(res["success"])
            self.assertIn("downloads", res.get("folder_name", "").lower())
            mock_popen.assert_called_once()

    def test_action_planner_desktop_intents(self):
        """Test ActionPlanner conversational parsing for desktop automation tools."""
        # 1. Open app and type
        with patch.object(desktop_controller, "open_and_type", return_value={"success": True}) as mock_open_type:
            plan = ActionPlanner.plan_and_execute("open notepad and type Hello AURA")
            self.assertIsNotNone(plan)
            self.assertEqual(plan.get("action"), "open_and_type")
            mock_open_type.assert_called_once_with("notepad", "Hello AURA")

        # 2. Type text into app
        with patch.object(desktop_controller, "open_and_type", return_value={"success": True}) as mock_open_type:
            plan = ActionPlanner.plan_and_execute("type meeting notes into notepad")
            self.assertIsNotNone(plan)
            self.assertEqual(plan.get("action"), "open_and_type")
            mock_open_type.assert_called_once_with("notepad", "meeting notes")

        # 3. Hotkey
        with patch.object(keyboard_controller, "hotkey", return_value=True) as mock_hotkey:
            plan = ActionPlanner.plan_and_execute("press ctrl+shift+esc")
            self.assertIsNotNone(plan)
            self.assertEqual(plan.get("action"), "keyboard_hotkey")
            mock_hotkey.assert_called_once_with("ctrl", "shift", "esc")

        # 4. Open folder
        with patch.object(file_explorer_controller, "open_folder", return_value={"success": True}) as mock_folder:
            plan = ActionPlanner.plan_and_execute("open downloads folder")
            self.assertIsNotNone(plan)
            self.assertEqual(plan.get("action"), "open_folder")
            mock_folder.assert_called_once_with("downloads")

        # 5. Media search & play on Spotify
        with patch.object(media_controller, "play_spotify", return_value={"success": True}) as mock_spot_play:
            plan = ActionPlanner.plan_and_execute("play Taylor Swift on spotify")
            self.assertIsNotNone(plan)
            self.assertEqual(plan.get("action"), "media_play")
            mock_spot_play.assert_called_once_with("Taylor Swift")

        with patch.object(media_controller, "search_spotify", return_value={"success": True}) as mock_spot_search:
            plan = ActionPlanner.plan_and_execute("search Taylor Swift on spotify")
            self.assertIsNotNone(plan)
            self.assertEqual(plan.get("action"), "media_search")
            mock_spot_search.assert_called_once_with("Taylor Swift")

        # 6. Follow-up selection
        media_controller.last_media_context = {"platform": "youtube", "query": "lofi"}
        with patch.object(media_controller, "select_result", return_value={"success": True, "selected_index": 2}) as mock_sel:
            plan = ActionPlanner.plan_and_execute("play the second result")
            self.assertIsNotNone(plan)
            self.assertEqual(plan.get("action"), "media_select_result")
            mock_sel.assert_called_once_with(2)

        # 7. Mouse move
        with patch.object(mouse_controller, "move_to", return_value=True) as mock_move:
            plan = ActionPlanner.plan_and_execute("move mouse to 600, 400")
            self.assertIsNotNone(plan)
            self.assertEqual(plan.get("action"), "mouse_move")
            mock_move.assert_called_once_with(600, 400, smooth=True, duration=0.3)

    def test_desktop_rest_api_endpoints(self):
        """Test FastAPI REST endpoints for desktop controller."""
        # 1. GET /api/desktop/status
        res = self.client.get("/api/desktop/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("mouse_position", data)
        self.assertIn("monitors", data)

        # 2. GET /api/desktop/windows
        res = self.client.get("/api/desktop/windows")
        self.assertEqual(res.status_code, 200)
        self.assertIn("windows", res.json())

        # 3. POST /api/desktop/emergency-abort
        res = self.client.post("/api/desktop/emergency-abort")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get("success"))


if __name__ == "__main__":
    unittest.main()
