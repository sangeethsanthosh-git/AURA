"""
Unit tests for Edge-TTS neural voice integration and unified TTS service.
"""

from pathlib import Path
import unittest
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import (
    TTS_ENGINE,
    EDGE_TTS_VOICE,
    EDGE_TTS_SAMPLE_RATE,
    PIPER_SAMPLE_RATE,
)
from backend.services.edge_tts_service import EdgeTTSService
from backend.services.tts_service import TTSService
from fastapi.testclient import TestClient
from backend.api.app import app


class TestEdgeTTSIntegration(unittest.TestCase):
    def setUp(self):
        self.edge = EdgeTTSService()
        self.tts = TTSService()
        self.client = TestClient(app)

    def test_01_edge_service_configuration(self):
        """Verify EdgeTTSService properties and 24 kHz high-fidelity sample rate."""
        self.assertEqual(self.edge.sample_rate, 24000)
        self.assertEqual(self.edge.voice, EDGE_TTS_VOICE)
        self.assertTrue(self.edge.is_ready(), "edge-tts package must be installed and importable.")

    def test_02_unified_tts_service_edge_mode(self):
        """Verify unified TTSService operates in edge mode with correct voice metadata."""
        tts_edge = TTSService(engine="edge")
        self.assertEqual(tts_edge.engine_name, "edge")
        self.assertEqual(tts_edge.voice_name, "Aria")
        self.assertEqual(tts_edge.sample_rate, 24000)
        self.assertTrue(tts_edge.is_ready())

    def test_03_unified_tts_service_piper_fallback_mode(self):
        """Verify unified TTSService fallback to Piper functions properly at 22050 Hz."""
        tts_piper = TTSService(engine="piper")
        self.assertEqual(tts_piper.engine_name, "piper")
        self.assertEqual(tts_piper.voice_name, "lessac-medium")
        self.assertEqual(tts_piper.sample_rate, 22050)
        self.assertTrue(tts_piper.is_ready())

    def test_04_health_endpoint_metadata(self):
        """Verify /health endpoint exposes TTS engine, voice, and sample rate."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("tts_engine", data)
        self.assertIn("tts_voice", data)
        self.assertIn("tts_sample_rate", data)
        self.assertEqual(data["tts_engine"], "edge")
        self.assertEqual(data["tts_voice"], "Aria")
        self.assertEqual(data["tts_sample_rate"], 24000)
        self.assertIn("available_voices", data)
        self.assertGreaterEqual(len(data["available_voices"]), 9)

    def test_05_voice_profiles_and_switching(self):
        """Verify available voices list and dynamic voice switching."""
        voices = self.tts.get_available_voices()
        self.assertGreaterEqual(len(voices), 9)
        voice_ids = [v["id"] for v in voices]
        self.assertIn("aria", voice_ids)
        self.assertIn("guy", voice_ids)
        self.assertIn("jenny", voice_ids)
        self.assertIn("christopher", voice_ids)
        self.assertIn("piper", voice_ids)

        # Switch to Guy
        profile = self.tts.set_voice("guy")
        self.assertEqual(profile["id"], "guy")
        self.assertEqual(self.tts.voice_name, "Guy")
        self.assertEqual(self.tts.engine_name, "edge")

        # Switch to Piper (instant fallback)
        profile_piper = self.tts.set_voice("piper")
        self.assertEqual(profile_piper["id"], "piper")
        self.assertEqual(self.tts.engine_name, "piper")
        self.assertEqual(self.tts.voice_name, "lessac-medium")

        # Switch back to Aria
        self.tts.set_voice("aria")
        self.assertEqual(self.tts.voice_name, "Aria")

    def test_06_audio_earcons_generation(self):
        """Verify listening and cancel chime methods execute without exception."""
        from backend.services.audio_service import AudioService
        audio = AudioService()
        audio.play_listening_chime(block=False)
        audio.play_cancel_chime()


if __name__ == "__main__":
    unittest.main()
