"""Speech-to-text provider adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from backend.config.config import Settings, settings
from backend.language.detector import LanguageDetector, LanguageRoute
from backend.voice.models import TranscriptionResult
from language_manager import LanguageManager
from speech_manager import SpeechManager


class SpeechToTextProvider(Protocol):
    engine: str

    def transcribe(self, audio_path: Path, duration_seconds: float = 0.0) -> TranscriptionResult:
        ...


class FasterWhisperProvider:
    """Local Faster-Whisper adapter using the existing SpeechManager."""

    engine = "faster-whisper"

    def __init__(
        self,
        language_manager: LanguageManager | None = None,
        config: Settings = settings,
    ) -> None:
        self.config = config
        self.language_manager = language_manager or LanguageManager()
        self._speech_manager: SpeechManager | None = None

    def transcribe(self, audio_path: Path, duration_seconds: float = 0.0) -> TranscriptionResult:
        try:
            result = self._manager().transcribe(audio_path)
        except Exception as exc:
            return TranscriptionResult(
                success=False,
                duration_seconds=duration_seconds,
                engine=self.engine,
                error=str(exc) or "Transcription failed.",
            )

        text = result.text.strip()
        if not text:
            return TranscriptionResult(
                success=False,
                language=result.language,
                confidence=result.confidence,
                duration_seconds=duration_seconds,
                engine=self.engine,
                error="I could not detect any speech in that recording.",
            )

        return TranscriptionResult(
            success=True,
            text=text,
            language=result.language,
            confidence=result.confidence,
            duration_seconds=duration_seconds,
            engine=self.engine,
        )

    def _manager(self) -> SpeechManager:
        if self._speech_manager is None:
            self._speech_manager = SpeechManager(
                language_manager=self.language_manager,
                model_size=self.config.stt_model,
                device=self.config.stt_device,
                compute_type=self.config.stt_compute_type,
            )
        return self._speech_manager


class ManglishWhisperCandidateProvider(FasterWhisperProvider):
    """Candidate provider for future Manglish benchmarking.

    The model is intentionally not auto-downloaded. It becomes usable only if
    explicitly configured and available through Faster-Whisper-compatible model
    loading.
    """

    engine = "whisper-small-manglish-candidate"

    def __init__(self, language_manager: LanguageManager | None = None, config: Settings = settings) -> None:
        super().__init__(language_manager, config)
        self.model_reference = "jona276/whisper-small-manglish"


class SpeechToTextRouter:
    """Routes STT provider choice while keeping models lazily loaded."""

    def __init__(
        self,
        default_provider: SpeechToTextProvider,
        manglish_provider: SpeechToTextProvider | None = None,
        detector: LanguageDetector | None = None,
    ) -> None:
        self.default_provider = default_provider
        self.manglish_provider = manglish_provider
        self.detector = detector or LanguageDetector()

    @property
    def engine(self) -> str:
        return self.default_provider.engine

    def transcribe(self, audio_path: Path, duration_seconds: float = 0.0) -> TranscriptionResult:
        # Audio-language pre-routing needs audio classification; for V1, keep the
        # reliable default provider and annotate text route after transcription.
        result = self.default_provider.transcribe(audio_path, duration_seconds)
        if result.success and result.text:
            detected = self.detector.detect(result.text)
            language = result.language
            if detected.route == LanguageRoute.MIXED:
                language = "mixed"
            elif detected.route == LanguageRoute.MALAYALAM:
                language = "ml"
            return TranscriptionResult(
                success=True,
                text=result.text,
                language=language,
                confidence=result.confidence,
                duration_seconds=result.duration_seconds,
                engine=result.engine,
            )
        return result
