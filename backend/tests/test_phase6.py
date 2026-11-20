"""
Unit tests for Phase 6 Optimization components:
- IPv4 normalization & HTTP keep-alive Session in OllamaService
- Streaming Ollama chat & cancellation
- Zero-disk Piper raw PCM & chunk streaming in TTSService
- Cached CPU INT8 beam=1 STT inference
- AudioService continuous PCM playback flag & cancellation
"""

from pathlib import Path
import threading
import unittest
import sys
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.ollama_service import OllamaService
from backend.services.tts_service import TTSService
from backend.services.stt_service import STTService
from backend.services.audio_service import AudioService


class TestPhase6(unittest.TestCase):
    def test_01_ollama_localhost_normalized_and_session(self):
        svc = OllamaService(base_url="http://localhost:11434")
        self.assertEqual(svc.base_url, "http://127.0.0.1:11434")
        self.assertIs(svc._get_session(), svc._get_session())

    def test_02_ollama_streaming_and_cancellation(self):
        ollama = OllamaService()
        if not ollama.check_connection():
            self.skipTest("Ollama server is not running.")

        tokens = list(
            ollama.chat_stream(
                [{"role": "user", "content": "Reply with the single word: ready."}]
            )
        )
        full = "".join(tokens).strip()
        self.assertGreater(len(full), 0)

        # Verify cancel_event stops stream early
        cancel = threading.Event()
        collected = []
        for tok in ollama.chat_stream(
            [{"role": "user", "content": "Count slowly from 1 to 20."}],
            cancel_event=cancel,
        ):
            collected.append(tok)
            if len(collected) >= 2:
                cancel.set()
        self.assertLessEqual(len(collected), 3)

    def test_03_tts_raw_pcm_and_stream(self):
        tts = TTSService(engine="piper")
        self.assertTrue(tts.is_ready())

        pcm = tts.synthesize_pcm("Testing raw PCM audio synthesis.")
        self.assertIsInstance(pcm, np.ndarray)
        self.assertEqual(pcm.dtype, np.float32)
        self.assertGreater(len(pcm), 1000)
        self.assertLessEqual(float(np.max(np.abs(pcm))), 1.0)

        chunks = list(tts.synthesize_pcm_stream("Streaming raw chunks."))
        self.assertGreaterEqual(len(chunks), 1)

    def test_04_stt_cached_cpu_int8(self):
        sample = PROJECT_ROOT / "assets" / "input_test.wav"
        if not sample.exists():
            self.skipTest("Sample input_test.wav not present.")
        stt = STTService()
        stt.load_model()
        self.assertTrue(stt.is_loaded())
        text = stt.transcribe(sample)
        self.assertIn("japan", text.lower())

    def test_05_audio_pcm_stream_stop(self):
        audio = AudioService()
        silence_chunk = np.zeros(2205, dtype=np.float32)  # 0.1s silence
        was_playing_during_chunk = []

        def _chunks():
            yield silence_chunk
            was_playing_during_chunk.append(audio.is_playing())

        audio.play_pcm_stream(_chunks(), sample_rate=22050)
        self.assertTrue(any(was_playing_during_chunk))
        self.assertFalse(audio.is_playing())


if __name__ == "__main__":
    unittest.main()
