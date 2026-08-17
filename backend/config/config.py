"""Configuration loading for AURA backend integrations.

The module intentionally avoids third-party dependencies so the current
offline-first project remains lightweight. Values are loaded from the process
environment first, then from a local ``.env`` file when present.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


def _load_dotenv(path: Path = ENV_FILE) -> None:
    """Load simple KEY=VALUE pairs without overriding existing variables."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Runtime settings shared by all online service adapters."""

    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    hf_api_key: str | None = os.getenv("HF_API_KEY")
    hf_model: str = os.getenv("HF_MODEL", "zai-org/GLM-5.2:featherless-ai")
    hf_api_base_url: str = os.getenv(
        "HF_API_BASE_URL",
        "https://router.huggingface.co/v1/chat/completions",
    )
    request_timeout: int = int(os.getenv("AURA_REQUEST_TIMEOUT", "30"))
    retry_attempts: int = int(os.getenv("AURA_RETRY_ATTEMPTS", "3"))
    retry_backoff_seconds: float = float(os.getenv("AURA_RETRY_BACKOFF_SECONDS", "1.0"))
    debug: bool = os.getenv("DEBUG", os.getenv("AURA_DEBUG", "False")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    location_api_url: str = os.getenv("LOCATION_API_URL", "https://ipapi.co/json/")
    nominatim_user_agent: str = os.getenv(
        "NOMINATIM_USER_AGENT",
        "AURA-MCA-MiniProject/1.0 (offline-first desktop assistant)",
    )
    default_country_code: str | None = os.getenv("AURA_DEFAULT_COUNTRY_CODE", "IN")
    voice_input_enabled: bool = os.getenv("AURA_VOICE_INPUT_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    stt_engine: str = os.getenv("AURA_STT_ENGINE", "faster-whisper")
    stt_model: str = os.getenv("AURA_STT_MODEL", "small")
    stt_device: str = os.getenv("AURA_STT_DEVICE", "cpu")
    stt_compute_type: str = os.getenv("AURA_STT_COMPUTE_TYPE", "int8")
    max_recording_duration_seconds: float = float(os.getenv("AURA_MAX_RECORDING_DURATION", "30"))
    auto_send_transcription: bool = os.getenv("AURA_AUTO_SEND_TRANSCRIPTION", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


settings = Settings()
