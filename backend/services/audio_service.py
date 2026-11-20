"""
Service for local audio capture, playback, and interruption management.
Supports low-latency pre-roll speech capture and gapless PCM streaming playback.
"""

from collections import deque
from pathlib import Path
from typing import Callable, Iterable, Optional
import time
import logging
import threading
import sounddevice as sd
import soundfile as sf
import numpy as np

from backend.config import (
    INPUT_SAMPLE_RATE,
    AUDIO_SAMPLE_RATE,
    SILENCE_ENERGY_THRESHOLD,
    SILENCE_DURATION_SECONDS,
    MAX_RECORDING_DURATION,
    MIN_RECORDING_DURATION,
)

logger = logging.getLogger(__name__)


class AudioService:
    def __init__(self):
        self._is_playing = False
        self._playback_lock = threading.Lock()
        self._cancel_record_event = threading.Event()
        self._cancel_play_event = threading.Event()
        self._active_output_stream: Optional[sd.OutputStream] = None

    def _create_output_stream(self, sample_rate: int) -> sd.OutputStream:
        """
        Create a robust sounddevice OutputStream for the current default audio device.
        Dynamically refreshes PortAudio in case a Bluetooth/USB headset was connected.
        """
        # Attempt 1: System default output device
        try:
            return sd.OutputStream(
                device=None,
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
            )
        except Exception as e1:
            logger.warning(f"Default OutputStream open failed ({e1}). Refreshing PortAudio device list...")

        # Attempt 2: Re-initialize PortAudio device list in case Bluetooth/USB headset state changed
        try:
            sd._terminate()
            sd._initialize()
            return sd.OutputStream(
                device=None,
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
            )
        except Exception as e2:
            logger.warning(f"Re-initialized default OutputStream open failed ({e2}). Searching for working output device...")

        # Attempt 3: Iterate through available output devices
        try:
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                if dev.get("max_output_channels", 0) > 0:
                    try:
                        return sd.OutputStream(
                            device=idx,
                            samplerate=sample_rate,
                            channels=1,
                            dtype="float32",
                        )
                    except Exception:
                        continue
        except Exception as e3:
            logger.error(f"Failed to query output devices: {e3}")

        # Final attempt: let sounddevice pick its default fallback
        return sd.OutputStream(samplerate=sample_rate, channels=1, dtype="float32")

    # ==========================
    # Playback & Interruption
    # ==========================
    def is_playing(self) -> bool:
        """Check if audio is actively playing (protects WakeWordService from loopback)."""
        if not self._is_playing:
            return False
        if self._active_output_stream is not None:
            try:
                return bool(self._active_output_stream.active)
            except Exception:
                return False
        try:
            stream = sd.get_stream()
            return bool(stream is not None and stream.active)
        except Exception:
            return self._is_playing

    def stop(self) -> None:
        """Immediately stop any active audio playback or recording."""
        self._cancel_record_event.set()
        self._cancel_play_event.set()
        if self._active_output_stream is not None:
            try:
                self._active_output_stream.abort()
            except Exception as e:
                logger.debug(f"Error aborting output stream: {e}")
        try:
            sd.stop()
        except Exception as e:
            logger.warning(f"Error stopping audio stream: {e}")
        finally:
            self._is_playing = False

    def play_listening_chime(self, block: bool = True) -> None:
        """
        Play a brief, friendly ascending two-tone earcon (C5 523Hz -> G5 784Hz)
        indicating AURA has begun listening. When block=True, completes before mic opens.
        """
        def _play():
            try:
                sr = 24000
                dur = 0.08
                segments = []
                for freq in [523.25, 783.99]:
                    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
                    env = np.exp(-3.5 * t / dur)
                    seg = np.sin(2 * np.pi * freq * t) * env * 0.22
                    segments.append(seg)
                audio = np.concatenate(segments).astype(np.float32)
                sd.play(audio, sr, device=None)
                sd.wait()
            except Exception as e:
                logger.debug(f"Listening chime note: {e}")

        if block:
            _play()
        else:
            threading.Thread(target=_play, daemon=True).start()

    def play_cancel_chime(self) -> None:
        """
        Play a soft descending two-tone earcon (E5 659Hz -> C5 523Hz)
        indicating speech cancellation or stop. Runs asynchronously.
        """
        def _play():
            try:
                sr = 24000
                dur = 0.07
                segments = []
                for freq in [659.25, 523.25]:
                    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
                    env = np.exp(-4.0 * t / dur)
                    seg = np.sin(2 * np.pi * freq * t) * env * 0.18
                    segments.append(seg)
                audio = np.concatenate(segments).astype(np.float32)
                sd.play(audio, sr, device=None)
                sd.wait()
            except Exception as e:
                logger.debug(f"Cancel chime note: {e}")

        threading.Thread(target=_play, daemon=True).start()

    def play_wav(self, file_path: str, block: bool = True) -> None:
        """Play a WAV file through the default audio output device."""
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {file_path}")

        self.stop()
        self._cancel_play_event.clear()
        data, sample_rate = sf.read(str(path), dtype="float32")

        with self._playback_lock:
            self._is_playing = True
            try:
                sd.play(data, sample_rate, device=None)
            except Exception:
                try:
                    sd._terminate()
                    sd._initialize()
                    sd.play(data, sample_rate, device=None)
                except Exception:
                    sd.play(data, sample_rate)

        if block:
            sd.wait()
            self._is_playing = False

    def play_pcm_stream(
        self,
        chunks: Iterable[np.ndarray],
        sample_rate: int = AUDIO_SAMPLE_RATE,
        on_playback_start: Optional[Callable[[], None]] = None,
        on_chunk_played: Optional[Callable[[float], None]] = None,
    ) -> None:
        """
        Stream 1D float32 PCM chunks continuously through a single OutputStream.
        Provides gapless playback across sentences and instant interruption.
        """
        self.stop()
        self._cancel_play_event.clear()

        started_notified = False
        with self._playback_lock:
            self._is_playing = True
            stream: Optional[sd.OutputStream] = None
            try:
                for chunk in chunks:
                    if self._cancel_play_event.is_set():
                        break
                    if chunk is None or len(chunk) == 0:
                        continue

                    # Lazy initialization of OutputStream on first chunk arrival
                    # Avoids starvation/timeout while upstream LLM & TTS are inferring
                    if stream is None:
                        stream = self._create_output_stream(sample_rate)
                        self._active_output_stream = stream
                        stream.start()

                    if not started_notified:
                        started_notified = True
                        if on_playback_start:
                            on_playback_start()

                    # Write expects (frames, channels) or contiguous float32 2D/1D matching channels
                    pcm = np.ascontiguousarray(chunk, dtype=np.float32).reshape(-1, 1)
                    if on_chunk_played:
                        try:
                            rms = float(np.sqrt(np.mean(chunk**2))) if len(chunk) > 0 else 0.0
                            level = min(1.0, rms * 3.5)
                            on_chunk_played(level)
                        except Exception:
                            pass
                    stream.write(pcm)
            finally:
                if stream is not None:
                    try:
                        stream.stop()
                        stream.close()
                    except Exception as close_err:
                        logger.debug(f"Error closing output stream: {close_err}")
                self._active_output_stream = None
                self._is_playing = False

    def play_wav_async(
        self,
        file_path: str,
        on_finished: Optional[Callable[[], None]] = None,
    ) -> threading.Thread:
        """Play a WAV file asynchronously in a separate thread."""
        def _worker():
            try:
                self.play_wav(file_path, block=True)
            except Exception as e:
                logger.error(f"Async playback error: {e}")
            finally:
                if on_finished:
                    on_finished()

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return thread

    # ==========================
    # Recording & Silence Detection
    # ==========================
    def record_speech(
        self,
        sample_rate: int = INPUT_SAMPLE_RATE,
        energy_threshold: float = SILENCE_ENERGY_THRESHOLD,
        silence_duration: float = SILENCE_DURATION_SECONDS,
        max_duration: float = MAX_RECORDING_DURATION,
        min_duration: float = MIN_RECORDING_DURATION,
        timeout: float = 7.0,
        on_speech_detected: Optional[Callable[[], None]] = None,
    ) -> np.ndarray:
        """
        Record audio from the microphone until user finishes speaking.

        Uses RMS energy detection + a 5-chunk (~320ms) pre-roll buffer:
        1. Keeps a short rolling pre-roll before speech starts so leading silence isn't fed to STT.
        2. Once speech starts, records continuously until trailing silence exceeds `silence_duration`.
        3. Supports instant cancellation via `audio_service.stop()`.
        """
        self._cancel_record_event.clear()
        chunk_size = 1024  # ~64ms at 16kHz
        pre_roll: deque[np.ndarray] = deque(maxlen=5)
        chunks: list[np.ndarray] = []
        speech_started = False
        silence_start_time: Optional[float] = None
        record_start_time = time.time()

        with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32") as stream:
            while True:
                if self._cancel_record_event.is_set():
                    logger.debug("Recording cancelled.")
                    return np.array([], dtype=np.float32)

                chunk, overflowed = stream.read(chunk_size)
                if overflowed:
                    logger.debug("Audio buffer overflowed.")

                chunk_flat = chunk.flatten()
                rms_energy = float(np.sqrt(np.mean(chunk_flat ** 2)))
                current_time = time.time()
                elapsed = current_time - record_start_time

                if not speech_started:
                    pre_roll.append(chunk_flat)
                    if rms_energy >= energy_threshold:
                        speech_started = True
                        chunks.extend(pre_roll)
                        if on_speech_detected:
                            on_speech_detected()
                    elif elapsed >= timeout:
                        logger.debug("Listening timeout reached with no speech.")
                        return np.array([], dtype=np.float32)
                else:
                    chunks.append(chunk_flat)
                    if rms_energy < energy_threshold:
                        if silence_start_time is None:
                            silence_start_time = current_time
                        elif (current_time - silence_start_time) >= silence_duration:
                            break
                    else:
                        silence_start_time = None

                    if elapsed >= max_duration:
                        logger.debug("Max recording duration reached.")
                        break

        if not chunks or not speech_started:
            return np.array([], dtype=np.float32)

        audio_data = np.concatenate(chunks, axis=0)
        total_duration = len(audio_data) / sample_rate

        if total_duration < min_duration:
            logger.debug(f"Recorded audio duration ({total_duration:.2f}s) under minimum ({min_duration}s).")
            return np.array([], dtype=np.float32)

        return audio_data

    def save_wav(self, audio_data: np.ndarray, file_path: str, sample_rate: int = INPUT_SAMPLE_RATE) -> str:
        """Save a numpy float32 audio array to a WAV file."""
        path = Path(file_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(path), audio_data, sample_rate)
        return str(path)
