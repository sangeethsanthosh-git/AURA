"""
Unit tests for Phase 4 Activation & Loopback components.
"""

from pathlib import Path
import unittest
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.audio_service import AudioService
from backend.services.wake_word_service import WakeWordService


class TestPhase4(unittest.TestCase):
    def setUp(self):
        self.audio = AudioService()
        self.ww = WakeWordService(audio_service=self.audio)

    def tearDown(self):
        self.ww.stop()

    def test_01_wake_phrase_positive_matches(self):
        self.assertTrue(self.ww.check_for_wake_phrase("Aura"))
        self.assertTrue(self.ww.check_for_wake_phrase("Hey Aura, are you there?"))
        self.assertTrue(self.ww.check_for_wake_phrase("AURA."))
        self.assertTrue(self.ww.check_for_wake_phrase("ora"))

    def test_02_wake_phrase_negative_rejection(self):
        self.assertFalse(self.ww.check_for_wake_phrase("Turn on the lights"))
        self.assertFalse(self.ww.check_for_wake_phrase("Hello Jarvis"))
        self.assertFalse(self.ww.check_for_wake_phrase("What is the time?"))

    def test_03_acoustic_loopback_flag(self):
        # When audio is not playing, loopback prevention is inactive
        self.assertFalse(self.audio.is_playing())

    def test_04_listener_lifecycle(self):
        self.assertFalse(self.ww.is_running)
        self.ww.start()
        self.assertTrue(self.ww.is_running)
        self.ww.stop()
        self.assertFalse(self.ww.is_running)


if __name__ == "__main__":
    unittest.main()
