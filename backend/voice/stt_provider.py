"""Speech-to-text provider adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from backend.config.config import Settings, settings
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
