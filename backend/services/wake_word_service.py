"""
Service for Wake-Word Activation ("AURA") and Push-to-Talk management.
Includes acoustic loopback prevention while assistant speaks.
"""

from typing import Callable, Optional
import time
import queue
import logging
import threading
import numpy as np
import sounddevice as sd

from backend.config import (
    INPUT_SAMPLE_RATE,
    WAKE_WORD_PHRASE,
    WAKE_WORD_ENGINE,
    OPENWAKEWORD_MODEL,
    WAKE_WORD_ENERGY_THRESHOLD,
)
from backend.services.stt_service import STTService
from backend.services.audio_service import AudioService

logger = logging.getLogger(__name__)


class WakeWordService:
    def __init__(
        self,
        audio_service: AudioService,
        stt_service: Optional[STTService] = None,
        on_wake_detected: Optional[Callable[[], None]] = None,
    ):
        self.audio_service = audio_service
        self.stt_service = stt_service
        self.on_wake_detected = on_wake_detected

        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._stream: Optional[sd.InputStream] = None
        self._audio_queue: queue.Queue = queue.Queue(maxsize=50)
        self._oww_model = None

        # Acceptable phonetic variants for "AURA" in Whisper
        self.target_keywords = {"aura", "ora", "hey aura", "hey ora", "aurora"}

        # Initialize openWakeWord if configured
        if WAKE_WORD_ENGINE == "openwakeword":
            self._init_openwakeword()

    def _init_openwakeword(self) -> None:
        """Initialize openWakeWord ONNX model."""
        try:
            from openwakeword.model import Model
            self._oww_model = Model(wakeword_models=[OPENWAKEWORD_MODEL])
            logger.info(f"openWakeWord initialized with model '{OPENWAKEWORD_MODEL}'.")
        except Exception as e:
            logger.warning(
                f"Could not load openWakeWord model '{OPENWAKEWORD_MODEL}': {e}. Falling back to AURA spotter."
            )

    def check_for_wake_phrase(self, text: str) -> bool:
        """Check if recognized speech text matches the AURA wake-word."""
        cleaned = text.lower().strip().replace(".", "").replace(",", "").replace("!", "")
        words = cleaned.split()
        return any(w in self.target_keywords for w in words) or any(
            phrase in cleaned for phrase in self.target_keywords
        )

    def start(self) -> None:
        """Start background wake-word listening with non-blocking callback stream."""
        if self.is_running:
            return

        self.is_running = True
        self._audio_queue = queue.Queue(maxsize=50)

        def _audio_callback(indata, frames, time_info, status):
            if not self.is_running:
                return
            # Acoustic loopback check: if speaker is playing, drop audio chunk
            if self.audio_service.is_playing():
                return
            try:
                self._audio_queue.put_nowait(indata.flatten().copy())
            except queue.Full:
                pass

        try:
            self._stream = sd.InputStream(
                samplerate=INPUT_SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=1280,  # ~80ms chunks
                callback=_audio_callback,
            )
            self._stream.start()
        except Exception as e:
            logger.error(f"Could not open microphone stream for wake-word: {e}")
            self.is_running = False
            return

        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        logger.info("Wake-Word callback listener started.")

    def stop(self) -> None:
        """Stop background wake-word listening and cleanly release stream."""
        self.is_running = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None
        logger.info("Wake-Word callback listener stopped.")

    def _process_loop(self) -> None:
        """Process audio chunks from callback queue for wake-word matching."""
        rolling_buffer = []
        max_buffer_len = int(1.4 * INPUT_SAMPLE_RATE)

        while self.is_running:
            try:
                chunk_flat = self._audio_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if self.audio_service.is_playing():
                rolling_buffer.clear()
                continue

            rms = float(np.sqrt(np.mean(chunk_flat ** 2)))
            if rms < WAKE_WORD_ENERGY_THRESHOLD and len(rolling_buffer) == 0:
                continue

            rolling_buffer.extend(chunk_flat)

            # openWakeWord prediction
            if self._oww_model is not None:
                pcm16_chunk = (chunk_flat * 32767).astype(np.int16)
                prediction = self._oww_model.predict(pcm16_chunk)
                for model_name, score in prediction.items():
                    if score >= 0.5:
                        logger.info(f"openWakeWord triggered by '{model_name}' (score: {score:.2f})")
                        rolling_buffer.clear()
                        if self.on_wake_detected:
                            self.on_wake_detected()
                        time.sleep(1.0)
                        break

            # AURA spotter
            if len(rolling_buffer) >= max_buffer_len:
                audio_window = np.array(rolling_buffer, dtype=np.float32)
                rolling_buffer.clear()

                if self.stt_service:
                    try:
                        detected_text = self.stt_service.transcribe(audio_window)
                        if detected_text and self.check_for_wake_phrase(detected_text):
                            logger.info(f"AURA wake-word recognized: \"{detected_text}\"")
                            if self.on_wake_detected:
                                self.on_wake_detected()
                            time.sleep(1.0)
                    except Exception as e:
                        logger.debug(f"Spotter transcription error: {e}")
