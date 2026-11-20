"""
Service for High-Fidelity Humanized Text-to-Speech synthesis using Edge-TTS Neural Voices.
Provides studio-grade natural human voices (Aria, Guy, Jenny, Christopher, Sonia, etc.)
with near-zero latency, zero GPU VRAM consumption, and free cloud neural synthesis.
"""

from pathlib import Path
from typing import Iterator, Optional
import asyncio
import io
import logging
import threading
import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


class EdgeTTSService:
    def __init__(
        self,
        default_voice: str = "en-US-AriaNeural",
        sample_rate: int = 24000,
    ):
        self.voice = default_voice
        self.sample_rate = sample_rate
        self.rate = "+0%"
        self.pitch = "+0Hz"

    def set_delivery_tuning(self, rate: str = "+0%", pitch: str = "+0Hz") -> None:
        """Dynamically adapt prosody/delivery speed and pitch based on active persona."""
        self.rate = rate
        self.pitch = pitch

    @property
    def speaker(self) -> str:
        """Name of active speaker voice."""
        return self.voice

    def is_ready(self) -> bool:
        """Check if edge-tts package is importable."""
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            return False

    def set_voice(self, voice_id: str) -> str:
        """Dynamically set the active neural voice."""
        self.voice = voice_id.strip()
        logger.info(f"Edge-TTS active voice set to: {self.voice}")
        return self.voice

    def _synthesize_bytes(self, text: str) -> bytes:
        """Internal synchronous helper to communicate with Edge-TTS."""
        import edge_tts

        async def _run() -> bytes:
            communicate = edge_tts.Communicate(text.strip(), self.voice, rate=self.rate, pitch=self.pitch)
            audio_buffer = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.extend(chunk["data"])
            return bytes(audio_buffer)

        # Run inside isolated event loop to support multi-threaded callers
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(_run())
        finally:
            loop.close()

    def synthesize(self, text: str, output_path: str) -> str:
        """Synthesize text into a WAV file using Edge-TTS."""
        if not text.strip():
            raise ValueError("Text for TTS synthesis cannot be empty.")

        output_file = Path(output_path).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        audio_bytes = self._synthesize_bytes(text)
        if not audio_bytes:
            raise RuntimeError("Edge-TTS returned empty audio.")

        data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        if data.ndim > 1:
            data = np.mean(data, axis=-1)

        # Peak normalization to 0.95 for optimal volume
        max_val = np.max(np.abs(data))
        if max_val > 1e-4:
            data = (data / max_val) * 0.95

        self.sample_rate = sr
        sf.write(str(output_file), data, sr)
        return str(output_file)

    def synthesize_pcm(self, text: str) -> np.ndarray:
        """
        Synthesize text directly to a 1D float32 numpy array in RAM.
        Zero disk I/O for ultra-low latency playback.
        """
        if not text.strip():
            return np.array([], dtype=np.float32)

        try:
            audio_bytes = self._synthesize_bytes(text)
            if not audio_bytes:
                return np.array([], dtype=np.float32)

            data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
            if data.ndim > 1:
                data = np.mean(data, axis=-1)

            max_val = np.max(np.abs(data))
            if max_val > 1e-4:
                data = (data / max_val) * 0.95

            self.sample_rate = sr
            return data
        except Exception as exc:
            logger.error(f"Edge-TTS PCM synthesis failed: {exc}", exc_info=True)
            raise RuntimeError(f"Edge-TTS PCM synthesis failed: {exc}") from exc

    def synthesize_pcm_stream(
        self,
        text: str,
        cancel_event: Optional[threading.Event] = None,
        chunk_samples: int = 4096,
    ) -> Iterator[np.ndarray]:
        """
        Stream synthesized float32 PCM in chunks directly to the audio player.
        Checks cancel_event between chunks for instant user interruption.
        """
        if not text.strip() or (cancel_event is not None and cancel_event.is_set()):
            return

        pcm_data = self.synthesize_pcm(text)
        if len(pcm_data) == 0:
            return

        total_len = len(pcm_data)
        for start_idx in range(0, total_len, chunk_samples):
            if cancel_event is not None and cancel_event.is_set():
                logger.info("Edge-TTS stream cancelled during chunk playback.")
                return

            end_idx = min(start_idx + chunk_samples, total_len)
            yield pcm_data[start_idx:end_idx]
