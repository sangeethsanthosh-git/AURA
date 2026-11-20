"""
Service for Local Speech-to-Text using Faster-Whisper.
"""

from pathlib import Path
from typing import Optional, Union
import logging
import numpy as np
from faster_whisper import WhisperModel
from backend.config import (
    WHISPER_MODEL_SIZE,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_CPU_THREADS,
    WHISPER_BEAM_SIZE,
)

logger = logging.getLogger(__name__)


class STTService:
    def __init__(
        self,
        model_size: str = WHISPER_MODEL_SIZE,
        device: str = WHISPER_DEVICE,
        compute_type: str = WHISPER_COMPUTE_TYPE,
        cpu_threads: int = WHISPER_CPU_THREADS,
        beam_size: int = WHISPER_BEAM_SIZE,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads
        self.beam_size = beam_size
        self._model: Optional[WhisperModel] = None

    def load_model(self) -> None:
        """Load Faster-Whisper model into memory (prefer local cache to skip network checks)."""
        if self._model is not None:
            return

        logger.info(
            f"Loading Faster-Whisper model '{self.model_size}' on {self.device} "
            f"({self.compute_type}, threads={self.cpu_threads})..."
        )
        try:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
                local_files_only=True,
            )
        except Exception:
            logger.info("Local cache miss; downloading Faster-Whisper model...")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
                local_files_only=False,
            )
        logger.info("Faster-Whisper model loaded successfully.")

    def is_loaded(self) -> bool:
        """Check if model is currently loaded in memory."""
        return self._model is not None

    def transcribe(self, audio: Union[str, Path, np.ndarray]) -> str:
        """
        Transcribe audio to English text.
        Accepts either a WAV file path or a 1D float32 numpy array at 16kHz.
        """
        if self._model is None:
            self.load_model()

        if isinstance(audio, (str, Path)):
            audio_input = str(audio)
        else:
            if audio.ndim > 1:
                audio = audio.flatten()
            if audio.dtype != np.float32:
                audio_input = audio.astype(np.float32)
            else:
                audio_input = audio

        segments, _info = self._model.transcribe(
            audio_input,
            language="en",
            beam_size=self.beam_size,
            vad_filter=True,  # Built-in Silero VAD to suppress silence hallucinations
            vad_parameters=dict(min_silence_duration_ms=400),
        )

        text_parts = [segment.text.strip() for segment in segments]
        transcription = " ".join(part for part in text_parts if part)
        return transcription.strip()
