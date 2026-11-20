"""
Tests for:
1. BUG 1: Google Search natural syntax routing ("search python tutorials on google")
2. BUG 2: Spotify search and play with Kawaii Pixel Cat Paw
3. BUG 3: "PLAY IT" intent routing to play/pause (not searching for "it"),
         YouTube dropdown dismissal, and timeline scrubber / seeking controls.
"""

import unittest
from unittest.mock import patch, MagicMock
from backend.services.action_planner import ActionPlanner
from backend.services.system_tool_service import SystemToolService
from backend.desktop.media_controller import MediaController


class TestMediaSearchPlaybackFixes(unittest.TestCase):
    def setUp(self):
        ActionPlanner.initialize_registry()

    def test_bug1_google_search_natural_syntax(self):
        """Verify 'search python tutorials on google' dispatches to browser search, not screen vision or chat."""
        with patch("backend.desktop.desktop_controller.desktop_controller.browser_search") as mock_b_search:
            mock_b_search.return_value = {"success": True, "browser": "chrome", "query": "python tutorials"}
            
            res = ActionPlanner.plan_and_execute("search python tutorials on google")
            self.assertIsNotNone(res)
            self.assertTrue(res.get("handled"))
            mock_b_search.assert_called_once_with("chrome", "python tutorials")

    def test_bug1_google_search_variants(self):
        """Verify other natural Google search query styles."""
        with patch("backend.desktop.desktop_controller.desktop_controller.browser_search") as mock_b_search:
            mock_b_search.return_value = {"success": True, "browser": "chrome", "query": "fastapi docs"}
            
            # "google fastapi docs"
            res = ActionPlanner.plan_and_execute("google fastapi docs")
            self.assertIsNotNone(res)
            self.assertTrue(res.get("handled"))
            mock_b_search.assert_called_with("chrome", "fastapi docs")

    def test_bug2_spotify_search_and_play_intent(self):
        """Verify 'open spotify and play senjudare song' dispatches to Spotify play."""
        with patch("backend.desktop.media_controller.media_controller.play_spotify") as mock_spot:
            mock_spot.return_value = {"action": "spotify_play", "platform": "spotify", "query": "senjudare", "success": True}
            
            res = ActionPlanner.plan_and_execute("open spotify and play senjudare song")
            self.assertIsNotNone(res)
            self.assertTrue(res.get("handled"))
            self.assertEqual(res.get("action"), "media_play")
            mock_spot.assert_called_once_with("senjudare")

    def test_bug2_spotify_play_on_spotify(self):
        """Verify 'play starboy on spotify' triggers Spotify playback."""
        with patch("backend.desktop.media_controller.media_controller.play_spotify") as mock_spot:
            mock_spot.return_value = {"action": "spotify_play", "platform": "spotify", "query": "starboy", "success": True}
            
            res = ActionPlanner.plan_and_execute("play starboy on spotify")
            self.assertIsNotNone(res)
            self.assertTrue(res.get("handled"))
            mock_spot.assert_called_once_with("starboy")

    def test_bug3_play_it_intent_dispatches_play_pause(self):
        """Verify 'PLAY IT' triggers media_play_pause and NEVER searches YouTube for 'IT'."""
        with patch("backend.desktop.media_controller.media_controller.play_pause") as mock_play_pause, \
             patch("backend.desktop.media_controller.media_controller.play_youtube") as mock_play_yt:
            mock_play_pause.return_value = {"action": "play_pause", "success": True}
            
            res = ActionPlanner.plan_and_execute("PLAY IT")
            self.assertIsNotNone(res)
            self.assertTrue(res.get("handled"))
            self.assertEqual(res.get("action"), "media_play_pause")
            mock_play_pause.assert_called_once()
            mock_play_yt.assert_not_called()

    def test_bug3_playback_control_tokens_guarded(self):
        """Verify 'resume', 'pause', 'play this', 'play music' don't search YouTube for literal tokens."""
        with patch("backend.desktop.media_controller.media_controller.play_pause") as mock_play_pause, \
             patch("backend.desktop.media_controller.media_controller.play_youtube") as mock_play_yt:
            mock_play_pause.return_value = {"action": "play_pause", "success": True}
            
            for cmd in ["resume", "pause", "play it", "play this", "play song", "resume it"]:
                res = ActionPlanner.plan_and_execute(cmd)
                self.assertIsNotNone(res, f"Failed for {cmd}")
                self.assertEqual(res.get("action"), "media_play_pause", f"Wrong action for {cmd}")
            mock_play_yt.assert_not_called()

    def test_bug3_next_and_previous_track(self):
        """Verify 'next song' and 'previous song' dispatch properly."""
        with patch("backend.desktop.media_controller.media_controller.next_track") as mock_next, \
             patch("backend.desktop.media_controller.media_controller.previous_track") as mock_prev:
            mock_next.return_value = {"action": "next_track", "success": True}
            mock_prev.return_value = {"action": "previous_track", "success": True}

            res1 = ActionPlanner.plan_and_execute("next song")
            self.assertIsNotNone(res1)
            mock_next.assert_called_once()

            res2 = ActionPlanner.plan_and_execute("previous song")
            self.assertIsNotNone(res2)
            mock_prev.assert_called_once()

    def test_bug3_seeking_relative_and_percentage(self):
        """Verify seeking forward, rewind, and percentage timeline control."""
        with patch("backend.desktop.media_controller.media_controller.seek_relative") as mock_rel, \
             patch("backend.desktop.media_controller.media_controller.seek_percentage") as mock_pct:
            mock_rel.return_value = {"action": "seek_relative", "success": True}
            mock_pct.return_value = {"action": "seek_percentage", "success": True}

            # Forward 10 seconds
            res_fwd = ActionPlanner.plan_and_execute("forward 10 seconds")
            self.assertIsNotNone(res_fwd)
            mock_rel.assert_called_with(10)

            # Rewind 10 seconds
            res_rew = ActionPlanner.plan_and_execute("rewind 10 seconds")
            self.assertIsNotNone(res_rew)
            mock_rel.assert_called_with(-10)

            # Seek to 50%
            res_pct = ActionPlanner.plan_and_execute("seek to 50%")
            self.assertIsNotNone(res_pct)
            mock_pct.assert_called_with(50)

            # Go to middle
            res_mid = ActionPlanner.plan_and_execute("go to middle")
            self.assertIsNotNone(res_mid)
            mock_pct.assert_called_with(50)


if __name__ == "__main__":
    unittest.main()
