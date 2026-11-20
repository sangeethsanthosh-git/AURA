"""
Unit tests for Phase 1 components.
"""

from pathlib import Path
import unittest
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import OLLAMA_MODEL
from backend.services.ollama_service import OllamaService
from backend.services.tts_service import TTSService
from backend.services.audio_service import AudioService


class TestPhase1(unittest.TestCase):
    def setUp(self):
        self.ollama = OllamaService()
        self.tts = TTSService(engine="piper")
        self.audio = AudioService()

    def test_01_ollama_connection(self):
        self.assertTrue(self.ollama.check_connection(), "Ollama should be reachable.")

    def test_02_ollama_model_available(self):
        self.assertTrue(
            self.ollama.check_model_available(OLLAMA_MODEL),
            f"Model '{OLLAMA_MODEL}' should be downloaded and available.",
        )

    def test_03_tts_engine_ready(self):
        self.assertTrue(self.tts.is_ready(), "Piper binary and voice model must be ready.")

    def test_04_tts_synthesis(self):
        test_wav = PROJECT_ROOT / "assets" / "unit_test.wav"
        output_path = self.tts.synthesize("Unit test speech synthesis.", str(test_wav))
        self.assertTrue(Path(output_path).exists(), "Synthesized WAV file must exist.")
        self.assertGreater(Path(output_path).stat().st_size, 1000, "WAV file should not be empty.")
        if Path(output_path).exists():
            Path(output_path).unlink()


if __name__ == "__main__":
    unittest.main()
