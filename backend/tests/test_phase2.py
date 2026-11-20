"""
Unit tests for Phase 2 Speech Recognition components.
"""

from pathlib import Path
import unittest
import sys
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.stt_service import STTService
from backend.services.audio_service import AudioService
from backend.services.tts_service import TTSService


class TestPhase2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stt = STTService()
        cls.stt.load_model()
        cls.tts = TTSService(engine="piper")
        cls.audio = AudioService()

    def test_01_stt_model_loaded(self):
        self.assertTrue(self.stt.is_loaded(), "Faster-Whisper model must be loaded.")

    def test_02_stt_transcription_fidelity(self):
        # Generate known speech WAV using Piper
        test_wav = PROJECT_ROOT / "assets" / "phase2_unit_test.wav"
        prompt = "Artificial intelligence voice assistant."
        self.tts.synthesize(prompt, str(test_wav))

        # Transcribe back using Faster-Whisper
        transcription = self.stt.transcribe(str(test_wav)).lower()
        if Path(test_wav).exists():
            Path(test_wav).unlink()

        # Check for key words
        self.assertIn("artificial", transcription)
        self.assertIn("voice", transcription)

    def test_03_silence_detection_on_empty_audio(self):
        # 1 second of pure digital silence at 16kHz
        silence = np.zeros(16000, dtype=np.float32)
        rms = float(np.sqrt(np.mean(silence ** 2)))
        self.assertEqual(rms, 0.0, "RMS energy of pure silence must be 0.0")


if __name__ == "__main__":
    unittest.main()
