import logging
from dataclasses import dataclass
from pathlib import Path

from language_manager import LanguageManager

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpeechRecognitionResult:
    text: str
    language: str | None
    confidence: float


class SpeechManager:
    def __init__(
        self,
        language_manager: LanguageManager,
        model_size: str = "small",
        device: str = "cuda",
        compute_type: str = "float16",
    ) -> None:
        self.language_manager = language_manager
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def transcribe(self, audio_path: Path) -> SpeechRecognitionResult:
        model = self._load_model()
        segments, info = model.transcribe(str(audio_path), language=None)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        confidence = self._language_confidence(info)
        language = getattr(info, "language", None)

        if language:
            self.language_manager.update_from_stt_detection(language, confidence)

        LOGGER.info(
            "STT detected language=%s confidence=%.3f",
            language,
            confidence,
        )
        return SpeechRecognitionResult(
            text=text,
            language=language,
            confidence=confidence,
        )

    def _load_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError(
                    "faster-whisper is not installed. Add it before using voice input."
                ) from exc

            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            LOGGER.info("Loaded Faster-Whisper model: %s", self.model_size)

        return self._model

    @staticmethod
    def _language_confidence(info) -> float:
        probability = getattr(info, "language_probability", None)
        if probability is None:
            return 0.0
        return float(probability)
