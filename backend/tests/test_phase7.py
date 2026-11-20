"""
Unit tests for Phase 7 Windows Desktop & System Control components.
Verifies system tools: volume adjustment, battery & hardware diagnostics,
media playback keys, app launching, clipboard reading, and intent routing.
"""

import unittest
from unittest.mock import patch, MagicMock
from backend.services.system_tool_service import SystemToolService


class TestPhase7(unittest.TestCase):
    """Test suite for Phase 7 System Tools & Function Calling."""

    def test_volume_mute_intent(self):
        """Verify mute intent is parsed and handled."""
        with patch("backend.services.system_tool_service._send_key") as mock_key:
            res = SystemToolService.execute_intent("please mute the audio")
            self.assertIsNotNone(res)
            self.assertTrue(res["handled"])
            self.assertEqual(res["action"], "volume")
            self.assertEqual(res["type"], "volume_mute")
            mock_key.assert_called_once()

    def test_volume_exact_set_intent(self):
        """Verify volume calibration intent with percentage."""
        with patch("backend.services.system_tool_service._send_key") as mock_key:
            res = SystemToolService.execute_intent("set volume to 60%")
            self.assertIsNotNone(res)
            self.assertTrue(res["handled"])
            self.assertEqual(res["action"], "volume")
            self.assertEqual(res["type"], "volume_set")
            self.assertEqual(res["data"]["percent"], 60)
            self.assertTrue(mock_key.call_count >= 2)

    def test_volume_up_down_intents(self):
        """Verify incremental volume adjustments."""
        with patch("backend.services.system_tool_service._send_key") as mock_key:
            res_up = SystemToolService.execute_intent("turn up the volume")
            self.assertIsNotNone(res_up)
            self.assertEqual(res_up["type"], "volume_up")

            res_down = SystemToolService.execute_intent("quieter please")
            self.assertIsNotNone(res_down)
            self.assertEqual(res_down["type"], "volume_down")

    def test_battery_diagnostics(self):
        """Verify battery level and power status reporting."""
        res = SystemToolService.execute_intent("how is my battery?")
        self.assertIsNotNone(res)
        self.assertTrue(res["handled"])
        self.assertEqual(res["action"], "battery")
        self.assertIn("percent", res["data"])
        self.assertIn("plugged", res["data"])
        self.assertIn("spoken_response", res)

    def test_ram_cpu_diagnostics(self):
        """Verify memory and processor performance metrics."""
        res = SystemToolService.execute_intent("check my ram usage")
        self.assertIsNotNone(res)
        self.assertTrue(res["handled"])
        self.assertEqual(res["action"], "system_specs")
        self.assertIn("ram_percent", res["data"])
        self.assertIn("cpu_percent", res["data"])
        self.assertIn("ram_free_gb", res["data"])

    def test_clipboard_inspection(self):
        """Verify clipboard reading and summary."""
        with patch("backend.services.system_tool_service.get_clipboard_text", return_value="Hello world testing clipboard"):
            res = SystemToolService.execute_intent("summarize my clipboard")
            self.assertIsNotNone(res)
            self.assertTrue(res["handled"])
            self.assertEqual(res["action"], "clipboard")
            self.assertTrue(res["data"]["has_text"])
            self.assertEqual(res["data"]["word_count"], 4)
            self.assertIn("Hello world", res["message"])

    def test_media_playback_controls(self):
        """Verify media key controls (play/pause, next, previous)."""
        with patch("backend.services.system_tool_service._send_key") as mock_key:
            res_play = SystemToolService.execute_intent("pause music")
            self.assertIsNotNone(res_play)
            self.assertEqual(res_play["action"], "media")
            self.assertEqual(res_play["type"], "play_pause")

            res_next = SystemToolService.execute_intent("next song")
            self.assertIsNotNone(res_next)
            self.assertEqual(res_next["type"], "next_track")

            res_prev = SystemToolService.execute_intent("previous track")
            self.assertIsNotNone(res_prev)
            self.assertEqual(res_prev["type"], "previous_track")

    def test_app_launcher_notepad(self):
        """Verify application launch targeting safe mapped apps."""
        with patch("subprocess.Popen") as mock_popen:
            res = SystemToolService.execute_intent("open notepad")
            self.assertIsNotNone(res)
            self.assertTrue(res["handled"])
            self.assertEqual(res["action"], "app_launch")
            self.assertEqual(res["data"]["app_name"], "Notepad")
            mock_popen.assert_called_once()

    def test_app_launcher_spotify_protocol(self):
        """Verify URI protocol launching for apps like Spotify."""
        with patch("os.startfile") as mock_startfile:
            res = SystemToolService.execute_intent("launch spotify")
            self.assertIsNotNone(res)
            self.assertEqual(res["data"]["app_name"], "Spotify")
            mock_startfile.assert_called_with("spotify:")

    def test_youtube_search_intent(self):
        """Verify YouTube web search automation."""
        with patch("webbrowser.open") as mock_wb:
            res = SystemToolService.execute_intent("search youtube for lo-fi hip hop")
            self.assertIsNotNone(res)
            self.assertTrue(res["handled"])
            self.assertEqual(res["action"], "web_search")
            self.assertEqual(res["data"]["platform"], "youtube")
            self.assertIn("youtube.com", res["data"]["url"])
            mock_wb.assert_called_once()

    def test_open_youtube_search_in_default_browser(self):
        """Verify 'Open YouTube search in default browser' opens YouTube instead of generic browser."""
        with patch("os.startfile") as mock_startfile:
            res = SystemToolService.execute_intent("Open YouTube search in default browser")
            self.assertIsNotNone(res)
            self.assertTrue(res["handled"])
            self.assertEqual(res["data"]["app_name"], "YouTube")
            mock_startfile.assert_called_with("https://www.youtube.com")

    def test_fuzzy_app_resolution_and_typos(self):
        """Verify fuzzy typo-tolerant resolution for slang and typing mistakes."""
        with patch("os.startfile"), patch("subprocess.Popen"):
            res_utube = SystemToolService.execute_intent("open u tube")
            self.assertEqual(res_utube["data"]["app_name"], "YouTube")

            res_yt = SystemToolService.execute_intent("open yt")
            self.assertEqual(res_yt["data"]["app_name"], "YouTube")

            res_val = SystemToolService.execute_intent("open valorent")
            self.assertEqual(res_val["data"]["app_name"], "VALORANT")

            res_crm = SystemToolService.execute_intent("open chorme")
            self.assertEqual(res_crm["data"]["app_name"], "Google Chrome")

            res_spf = SystemToolService.execute_intent("open spotfy")
            self.assertEqual(res_spf["data"]["app_name"], "Spotify")

    def test_dynamic_game_launcher_valorant(self):
        """Verify dynamic Windows shortcut discovery and launching for games like Valorant."""
        with patch("os.startfile") as mock_startfile:
            res = SystemToolService.execute_intent("open valorant")
            self.assertIsNotNone(res)
            self.assertTrue(res["handled"])
            self.assertEqual(res["action"], "app_launch")
            self.assertIn("valorant", res["spoken_response"].lower())
            mock_startfile.assert_called_once()
            self.assertTrue(mock_startfile.call_args[0][0].lower().endswith(".lnk") or "valorant" in mock_startfile.call_args[0][0].lower())

    def test_web_service_launcher_youtube(self):
        """Verify web app launching for sites like YouTube."""
        with patch("os.startfile") as mock_startfile:
            res = SystemToolService.execute_intent("open youtube")
            self.assertIsNotNone(res)
            self.assertTrue(res["handled"])
            self.assertEqual(res["action"], "app_launch")
            self.assertEqual(res["data"]["app_name"], "YouTube")
            mock_startfile.assert_called_with("https://www.youtube.com")

    def test_app_not_found_graceful_response(self):
        """Verify uninstalled app query returns handled: True with clear not found response, preventing LLM hallucination."""
        res = SystemToolService.execute_intent("open totallynonexistentapp12345")
        self.assertIsNotNone(res)
        self.assertTrue(res["handled"])
        self.assertEqual(res["action"], "app_launch")
        self.assertFalse(res["data"]["found"])
        self.assertIn("couldn't find", res["spoken_response"].lower())

    def test_non_system_query_passthrough(self):
        """Verify factual or conversational prompts are NOT intercepted by system tools."""
        res_fact = SystemToolService.execute_intent("who was napoleon bonaparte")
        self.assertIsNone(res_fact)

        res_math = SystemToolService.execute_intent("what is quantum computing")
        self.assertIsNone(res_math)


if __name__ == "__main__":
    unittest.main()
