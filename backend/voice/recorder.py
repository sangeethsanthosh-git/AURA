"""Microphone recording helpers for push-to-talk voice input."""

from __future__ import annotations

import logging
import tempfile
import time
import wave
from pathlib import Path
from typing import Protocol

LOGGER = logging.getLogger(__name__)


class RecordingError(RuntimeError):
    """Raised when microphone capture cannot start or finish cleanly."""


class AudioRecorder(Protocol):
    def start(self, path: Path, max_duration_seconds: float) -> None:
        ...

    def stop(self) -> float:
        ...


class TempAudioFactory:
    """Creates temporary WAV paths for one-shot microphone recordings."""

    def create(self) -> Path:
        handle = tempfile.NamedTemporaryFile(prefix="aura_voice_", suffix=".wav", delete=False)
        path = Path(handle.name)
        handle.close()
        return path


class SoundDeviceAudioRecorder:
    """Records microphone audio with sounddevice without blocking the UI thread."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self._stream = None
        self._frames: list[object] = []
        self._path: Path | None = None
        self._started_at = 0.0
        self._max_duration_seconds = 0.0

    def start(self, path: Path, max_duration_seconds: float) -> None:
        if self._stream is not None:
            raise RecordingError("A recording is already active.")

        try:
            import sounddevice as sd
        except ImportError as exc:
            raise RecordingError("Microphone support requires the sounddevice package.") from exc

        self._frames = []
        self._path = path
        self._started_at = time.monotonic()
        self._max_duration_seconds = max_duration_seconds

        def callback(indata, frames, time_info, status) -> None:
            if status:
                LOGGER.warning("Microphone status: %s", status)
            if time.monotonic() - self._started_at <= self._max_duration_seconds:
                self._frames.append(indata.copy())

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                callback=callback,
            )
            self._stream.start()
        except Exception as exc:
            self._stream = None
            self._path = None
            raise RecordingError("Could not start microphone recording.") from exc

    def stop(self) -> float:
        if self._stream is None or self._path is None:
            raise RecordingError("No active microphone recording.")

        duration = max(0.0, time.monotonic() - self._started_at)
        try:
            self._stream.stop()
            self._stream.close()
            self._write_wav(self._path)
        except Exception as exc:
            raise RecordingError("Could not finish microphone recording.") from exc
        finally:
            self._stream = None
            self._path = None
            self._frames = []

        return duration

    def _write_wav(self, path: Path) -> None:
        if not self._frames:
            path.write_bytes(b"")
            return

        import numpy as np

        audio = np.concatenate(self._frames, axis=0)
        audio = np.clip(audio, -1.0, 1.0)
        pcm = (audio * 32767).astype(np.int16)

        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(self.channels)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(pcm.tobytes())
