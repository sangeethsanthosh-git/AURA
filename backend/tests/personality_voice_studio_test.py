from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from app import build_assistant_output
from backend.language.detector import LanguageDetector, LanguageRoute
from backend.personality import DEFAULT_PERSONALITY
from backend.session_context import SessionContext
from backend.voice.models import TranscriptionResult
from backend.voice.stt_provider import SpeechToTextRouter
from backend.voice_studio.manager import VoiceStudioManager
from backend.voice_studio.benchmark import benchmark_plan
from backend.voice_studio.models import VoiceEngine
from backend.voice_studio.normalization import SpeechNormalizer
from backend.voice_studio.registry import VoiceRegistry
from conversation_manager import ConversationManager
from language_manager import LanguageManager
from model_router import ModelRouter, ModelSelection
from tts_manager import TTSManager


class FakeOllama:
    def __init__(self) -> None:
        self.messages = []

    def chat(self, model, messages, stream=False):
        self.messages = messages
        return type("Result", (), {"content": "RAG has retrieval and generation parts."})()


class FakeRouter:
    def select_model(self, language):
        return ModelSelection(language=language, model="fake-model")


class FakeSTT:
    engine = "fake-stt"

    def __init__(self, text: str) -> None:
        self.text = text

    def transcribe(self, audio_path: Path, duration_seconds: float = 0.0):
        return TranscriptionResult(True, self.text, "en", 0.9, duration_seconds, self.engine)


class PersonalityVoiceStudioTest(unittest.TestCase):
    def test_personality_prompt_is_centralized(self) -> None:
        prompt = DEFAULT_PERSONALITY.system_prompt("Answer in English.")
        self.assertIn("AURA", prompt)
        self.assertIn("Avoid repetitive openings", prompt)

    def test_session_context_resolves_followup_topic(self) -> None:
        context = SessionContext()
        context.add_turn("user", "Tell me about RAG.")
        context.add_turn("assistant", "RAG combines retrieval and generation.")
        relevant = context.relevant_context_for("What are its disadvantages?")
        self.assertIn("RAG", relevant)
        self.assertIn("Recent turns", relevant)

    def test_conversation_manager_injects_session_context(self) -> None:
        fake = FakeOllama()
        manager = ConversationManager(LanguageManager(), FakeRouter(), ollama_client=fake)
        manager.ask("Tell me about RAG.")
        manager.ask("What are its disadvantages?")
        system = fake.messages[0].content
        self.assertIn("Session context", system)
        self.assertIn("RAG", system)

    def test_language_detector_handles_malayalam_manglish_and_mixed(self) -> None:
        detector = LanguageDetector()
        self.assertEqual(detector.detect("എങ്ങനെ ഉണ്ട്?").route, LanguageRoute.MALAYALAM)
        self.assertEqual(detector.detect("entha cheyyunne?").route, LanguageRoute.MIXED)
        self.assertEqual(detector.detect("ee Python code onn explain cheyyamo?").route, LanguageRoute.MIXED)
        self.assertEqual(detector.detect("How are you?").route, LanguageRoute.ENGLISH)

    def test_speech_normalizer_separates_display_from_spoken_text(self) -> None:
        text = "Here is code:\n```python\nprint('Hello')\n```\nSee https://example.com and RAG."
        spoken = SpeechNormalizer().normalize(text, "en")
        self.assertNotIn("```", spoken)
        self.assertNotIn("https://example.com", spoken)
        self.assertIn("R A G", spoken)

    def test_voice_registry_marks_candidates_unavailable(self) -> None:
        profiles = VoiceRegistry().profiles()
        engines = {profile.engine for profile in profiles}
        self.assertIn(VoiceEngine.PIPER, engines)
        candidates = [profile for profile in profiles if profile.engine != VoiceEngine.PIPER]
        self.assertTrue(candidates)
        self.assertTrue(all(not profile.availability for profile in candidates))

    def test_voice_studio_selects_language_profile(self) -> None:
        studio = VoiceStudioManager()
        self.assertEqual(studio.select_profile("en").id, "piper-en-lessac")
        self.assertEqual(studio.select_profile("ml").id, "piper-ml-meera")

    def test_tts_manager_uses_voice_studio_wrapper(self) -> None:
        studio = Mock()
        studio.piper_path = Path("piper")
        studio.output_dir = Path("output")
        studio.registry.get.side_effect = lambda profile_id: type("Profile", (), {"model_reference": Path(profile_id)})()
        manager = TTSManager(studio)
        manager.speak("Hello", "en")
        studio.speak.assert_called_once_with("Hello", "en")

    def test_build_assistant_output_has_spoken_text(self) -> None:
        output = build_assistant_output(
            {
                "ok": True,
                "provider": "ollama",
                "action": "chat",
                "message": "See `code` at https://example.com",
                "data": {},
                "route": {"language": "English", "provider": "Ollama", "model": "fake", "source": "Local AI"},
            }
        )
        self.assertEqual(output.assistant_message, "See `code` at https://example.com")
        self.assertNotIn("https://example.com", output.spoken_text or "")

    def test_stt_router_marks_manglish_transcript_as_mixed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "audio.wav"
            path.write_bytes(b"fake")
            router = SpeechToTextRouter(FakeSTT("ee Python code onn explain cheyyamo?"))
            result = router.transcribe(path, 0.1)
        self.assertTrue(result.success)
        self.assertEqual(result.language, "mixed")

    def test_benchmark_plan_lists_candidate_models_without_enabling_them(self) -> None:
        plan = benchmark_plan()
        self.assertIn("ai4bharat/IndicF5", plan["tts_candidates"])
        self.assertIn("jona276/whisper-small-manglish", plan["asr_candidates"])
        self.assertIn("not auto-installed", plan["note"])


if __name__ == "__main__":
    unittest.main()
