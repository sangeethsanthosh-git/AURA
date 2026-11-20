"""
Unified Text-to-Speech (TTS) Service for AURA Voice Assistant.
Supports:
1. Edge-TTS Neural Voices for ultra-humanized, expressive natural conversational speech.
2. Piper TTS (Local ONNX) for fast, lightweight offline fallback speech synthesis.
"""

from pathlib import Path
from typing import Iterator, Optional
import subprocess
import threading
import logging
import shutil
import os
import numpy as np

from backend.config import (
    BASE_DIR,
    PIPER_MODEL_PATH,
    PIPER_CONFIG_PATH,
    PIPER_SAMPLE_RATE,
    TTS_ENGINE,
    EDGE_TTS_VOICE,
    EDGE_TTS_SAMPLE_RATE,
)
from backend.services.edge_tts_service import EdgeTTSService

logger = logging.getLogger(__name__)


def _get_subprocess_flags() -> dict:
    """Returns Windows startup flags to completely prevent console/terminal window flickering."""
    flags = {}
    if os.name == "nt":
        flags["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE
        flags["startupinfo"] = si
    return flags


class PiperTTSBackend:
    """Piper ONNX binary backend for local offline synthesis."""

    def __init__(
        self,
        model_path: str = PIPER_MODEL_PATH,
        config_path: str = PIPER_CONFIG_PATH,
        piper_binary: str | None = None,
    ):
        self.model_path = Path(model_path)
        self.config_path = Path(config_path)
        self.sample_rate = PIPER_SAMPLE_RATE
        self.length_scale: float = 1.0

        # Detect Piper binary
        bundled_piper = BASE_DIR / "assets" / "piper" / "piper.exe"
        if piper_binary and Path(piper_binary).exists():
            self.piper_binary = str(piper_binary)
        elif bundled_piper.exists():
            self.piper_binary = str(bundled_piper)
        else:
            path_bin = shutil.which("piper")
            self.piper_binary = path_bin if path_bin else "piper"

    def is_ready(self) -> bool:
        """Check if both the Piper binary and voice model files exist."""
        binary_exists = (
            Path(self.piper_binary).exists()
            if os.path.isabs(self.piper_binary)
            else shutil.which(self.piper_binary) is not None
        )
        model_exists = self.model_path.exists()
        return bool(binary_exists and model_exists)

    def _build_base_cmd(self) -> list[str]:
        cmd = [
            self.piper_binary,
            "--model",
            str(self.model_path.resolve()),
        ]
        if self.config_path.exists():
            cmd.extend(["--config", str(self.config_path.resolve())])
        if abs(self.length_scale - 1.0) > 0.01:
            cmd.extend(["--length_scale", f"{self.length_scale:.2f}"])
        return cmd

    def synthesize(self, text: str, output_path: str) -> str:
        """Synthesize text into a WAV file using Piper."""
        if not text.strip():
            raise ValueError("Text for TTS synthesis cannot be empty.")

        if not self.is_ready():
            raise RuntimeError(
                f"TTS engine not ready. Binary: '{self.piper_binary}', Model: '{self.model_path}'"
            )

        output_file = Path(output_path).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        cmd = self._build_base_cmd() + [
            "--output_file",
            str(output_file),
            "--quiet",
        ]

        try:
            subprocess.run(
                cmd,
                input=text.strip().encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                **_get_subprocess_flags(),
            )
            return str(output_file)
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode("utf-8", errors="replace")
            logger.error(f"Piper TTS synthesis failed: {err_msg}")
            raise RuntimeError(f"Piper TTS synthesis failed: {err_msg}") from e

    def synthesize_pcm(self, text: str) -> np.ndarray:
        """Synthesize text directly to a 1D float32 numpy array in RAM (`--output_raw`)."""
        if not text.strip():
            return np.array([], dtype=np.float32)

        if not self.is_ready():
            raise RuntimeError(
                f"TTS engine not ready. Binary: '{self.piper_binary}', Model: '{self.model_path}'"
            )

        cmd = self._build_base_cmd() + ["--output_raw", "--quiet"]
        try:
            proc = subprocess.run(
                cmd,
                input=text.strip().encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                **_get_subprocess_flags(),
            )
            if not proc.stdout:
                return np.array([], dtype=np.float32)
            even_len = len(proc.stdout) - (len(proc.stdout) % 2)
            int16_audio = np.frombuffer(proc.stdout[:even_len], dtype=np.int16)
            return int16_audio.astype(np.float32) / 32768.0
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode("utf-8", errors="replace")
            logger.error(f"Piper raw PCM synthesis failed: {err_msg}")
            raise RuntimeError(f"Piper raw PCM synthesis failed: {err_msg}") from e

    def synthesize_pcm_stream(
        self,
        text: str,
        cancel_event: Optional[threading.Event] = None,
        chunk_bytes: int = 8192,
    ) -> Iterator[np.ndarray]:
        """Stream synthesized float32 PCM chunks directly from Piper stdout."""
        if not text.strip():
            return

        if not self.is_ready():
            raise RuntimeError(
                f"TTS engine not ready. Binary: '{self.piper_binary}', Model: '{self.model_path}'"
            )

        cmd = self._build_base_cmd() + ["--output_raw", "--quiet"]
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **_get_subprocess_flags(),
        )

        try:
            assert proc.stdin is not None and proc.stdout is not None
            proc.stdin.write(text.strip().encode("utf-8"))
            proc.stdin.close()

            remainder = b""
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    proc.kill()
                    return

                raw = proc.stdout.read(chunk_bytes)
                if not raw:
                    break

                buf = remainder + raw
                even_len = len(buf) - (len(buf) % 2)
                remainder = buf[even_len:]
                if even_len > 0:
                    int16_chunk = np.frombuffer(buf[:even_len], dtype=np.int16)
                    yield int16_chunk.astype(np.float32) / 32768.0
        finally:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
            if proc.stdout and not proc.stdout.closed:
                proc.stdout.close()
            if proc.stderr and not proc.stderr.closed:
                proc.stderr.close()
            if proc.poll() is None:
                proc.kill()
            proc.wait()


# Preset Humanized Voice Profiles across Neural Voices and Piper (offline)
VOICE_PROFILES = [
    {
        "id": "aria",
        "name": "Aria",
        "gender": "Female",
        "engine": "edge",
        "speaker": "en-US-AriaNeural",
        "badge": "Neural (Default)",
        "description": "Warm, highly expressive, natural conversational female voice",
    },
    {
        "id": "guy",
        "name": "Guy",
        "gender": "Male",
        "engine": "edge",
        "speaker": "en-US-GuyNeural",
        "badge": "Neural",
        "description": "Natural, relaxed, conversational American male voice",
    },
    {
        "id": "jenny",
        "name": "Jenny",
        "gender": "Female",
        "engine": "edge",
        "speaker": "en-US-JennyNeural",
        "badge": "Neural",
        "description": "Friendly, clear, and cheerful modern female voice",
    },
    {
        "id": "christopher",
        "name": "Christopher",
        "gender": "Male",
        "engine": "edge",
        "speaker": "en-US-ChristopherNeural",
        "badge": "Neural",
        "description": "Confident, authoritative, and articulate male voice",
    },
    {
        "id": "eric",
        "name": "Eric",
        "gender": "Male",
        "engine": "edge",
        "speaker": "en-US-EricNeural",
        "badge": "Neural",
        "description": "Youthful, energetic, and engaging male voice",
    },
    {
        "id": "ana",
        "name": "Ana",
        "gender": "Female",
        "engine": "edge",
        "speaker": "en-US-AnaNeural",
        "badge": "Neural",
        "description": "Gentle, soft, and soothing female voice",
    },
    {
        "id": "sonia",
        "name": "Sonia",
        "gender": "Female",
        "engine": "edge",
        "speaker": "en-GB-SoniaNeural",
        "badge": "British",
        "description": "Refined and elegant British English female voice",
    },
    {
        "id": "ryan",
        "name": "Ryan",
        "gender": "Male",
        "engine": "edge",
        "speaker": "en-GB-RyanNeural",
        "badge": "British",
        "description": "Natural, conversational British English male voice",
    },
    {
        "id": "piper",
        "name": "Piper (Lessac)",
        "gender": "Female",
        "engine": "piper",
        "speaker": "lessac-medium",
        "badge": "Offline <20ms",
        "description": "Ultra-fast offline local ONNX voice with zero latency",
    },
]


class TTSService:
    """
    Unified TTS Service supporting Edge-TTS Neural Voices and Piper (offline fallback).
    """

    def __init__(
        self,
        model_path: str = PIPER_MODEL_PATH,
        config_path: str = PIPER_CONFIG_PATH,
        piper_binary: str | None = None,
        engine: Optional[str] = None,
    ):
        self.engine = (engine or TTS_ENGINE).lower()
        self._piper = PiperTTSBackend(
            model_path=model_path,
            config_path=config_path,
            piper_binary=piper_binary,
        )
        self._edge = EdgeTTSService(default_voice=EDGE_TTS_VOICE, sample_rate=EDGE_TTS_SAMPLE_RATE)

    @property
    def sample_rate(self) -> int:
        """Active sample rate in Hz (24000 for Edge-TTS, 22050 for Piper)."""
        if self.engine == "edge" and self._edge.is_ready():
            return self._edge.sample_rate
        return self._piper.sample_rate

    @property
    def engine_name(self) -> str:
        """Name of active TTS engine."""
        if self.engine == "edge" and self._edge.is_ready():
            return "edge"
        return "piper"

    @property
    def voice_name(self) -> str:
        """Name of active speaker voice."""
        if self.engine == "edge" and self._edge.is_ready():
            for p in VOICE_PROFILES:
                if p["speaker"] == self._edge.voice or p["id"] == self._edge.voice.lower():
                    return p["name"]
            return self._edge.voice
        return "lessac-medium"

    def get_available_voices(self) -> list[dict]:
        """Return list of supported voice profiles."""
        return VOICE_PROFILES

    def set_voice(self, voice_id: str) -> dict:
        """
        Dynamically switch speaker persona or TTS engine.
        Accepts voice id, name, or speaker name.
        """
        v_clean = voice_id.lower().strip().replace(" ", "_").replace("-", "_")
        aliases = {"serena": "aria", "vivian": "jenny", "aiden": "eric"}
        if v_clean in aliases:
            v_clean = aliases[v_clean]
        for profile in VOICE_PROFILES:
            if (
                profile["id"] == v_clean
                or profile["name"].lower() == voice_id.lower()
                or profile["speaker"].lower() == v_clean
                or profile["speaker"].lower() == voice_id.lower()
            ):
                if profile["engine"] == "piper":
                    self.engine = "piper"
                else:
                    self.engine = "edge"
                    self._edge.set_voice(profile["speaker"])
                logger.info(
                    f"Active voice switched to: {profile['name']} (Engine: {self.engine}, Speaker: {profile['speaker']})"
                )
                return profile

        logger.warning(f"Voice '{voice_id}' not found. Defaulting to Aria.")
        self.engine = "edge"
        self._edge.set_voice("en-US-AriaNeural")
        return VOICE_PROFILES[0]

    def set_delivery_tuning(self, rate: str = "+0%", pitch: str = "+0Hz", length_scale: float = 1.0) -> None:
        """Adapts prosody, pacing, and pitch naturally based on active personality profile."""
        self._edge.set_delivery_tuning(rate=rate, pitch=pitch)
        self._piper.length_scale = length_scale

    def is_ready(self) -> bool:
        """Check if active or fallback TTS engine is ready."""
        if self.engine == "edge":
            if self._edge.is_ready():
                return True
            return self._piper.is_ready()
        return self._piper.is_ready()

    def synthesize(self, text: str, output_path: str) -> str:
        """Synthesize text to WAV file."""
        if self.engine == "edge" and self._edge.is_ready():
            try:
                return self._edge.synthesize(text, output_path)
            except Exception as exc:
                logger.warning(
                    f"Edge-TTS synthesis failed ({exc}), falling back to Piper."
                )
                return self._piper.synthesize(text, output_path)
        return self._piper.synthesize(text, output_path)

    def synthesize_pcm(self, text: str) -> np.ndarray:
        """Synthesize text directly to in-memory float32 PCM numpy array."""
        if self.engine == "edge" and self._edge.is_ready():
            try:
                return self._edge.synthesize_pcm(text)
            except Exception as exc:
                logger.warning(
                    f"Edge-TTS PCM synthesis failed ({exc}), falling back to Piper."
                )
                return self._piper.synthesize_pcm(text)
        return self._piper.synthesize_pcm(text)

    def synthesize_pcm_stream(
        self,
        text: str,
        cancel_event: Optional[threading.Event] = None,
        chunk_bytes: int = 8192,
    ) -> Iterator[np.ndarray]:
        """Stream synthesized float32 PCM chunks."""
        if self.engine == "edge" and self._edge.is_ready():
            try:
                yield from self._edge.synthesize_pcm_stream(text, cancel_event=cancel_event)
                return
            except Exception as exc:
                logger.warning(
                    f"Edge-TTS stream failed ({exc}), falling back to Piper."
                )
                yield from self._piper.synthesize_pcm_stream(
                    text, cancel_event=cancel_event, chunk_bytes=chunk_bytes
                )
                return
        yield from self._piper.synthesize_pcm_stream(
            text, cancel_event=cancel_event, chunk_bytes=chunk_bytes
        )
