"""Configuration loading for AURA backend integrations.

The module intentionally avoids third-party dependencies so the current
offline-first project remains lightweight. Values are loaded from the process
environment first, then from a local ``.env`` file when present.
"""

from __future__ import annotations

import os
import json
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


def _split_keys(*values: str | None) -> tuple[str, ...]:
    keys: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        for item in value.replace("\n", ",").split(","):
            key = item.strip()
            if key and key not in seen:
                keys.append(key)
                seen.add(key)
    return tuple(keys)


def _load_provider_key_file() -> dict[str, tuple[str, ...]]:
    raw_path = os.getenv("AURA_PROVIDER_KEYS_FILE")
    if not raw_path:
        return {}
    path = Path(raw_path).expanduser()
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(parsed, list):
        return {}
    grouped: dict[str, list[str]] = {"groq": [], "huggingface": [], "nvidia": []}
    for item in parsed:
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider") or "").lower()
        value = str(item.get("value") or "").strip()
        if provider in grouped and value:
            grouped[provider].append(value)
    return {key: tuple(values) for key, values in grouped.items()}


_PROVIDER_KEY_FILE = _load_provider_key_file()


@dataclass(frozen=True)
class Settings:
    """Runtime settings shared by all online service adapters."""

    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_api_keys: tuple[str, ...] = _split_keys(os.getenv("GROQ_API_KEYS"), os.getenv("GROQ_API_KEY"), *_PROVIDER_KEY_FILE.get("groq", ()))
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    hf_api_key: str | None = os.getenv("HF_API_KEY")
    hf_api_keys: tuple[str, ...] = _split_keys(os.getenv("HF_API_KEYS"), os.getenv("HF_API_KEY"), *_PROVIDER_KEY_FILE.get("huggingface", ()))
    hf_model: str = os.getenv("HF_MODEL", "zai-org/GLM-5.2:featherless-ai")
    hf_api_base_url: str = os.getenv(
        "HF_API_BASE_URL",
        "https://router.huggingface.co/v1/chat/completions",
    )
    nvidia_api_key: str | None = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY")
    nvidia_api_keys: tuple[str, ...] = _split_keys(
        os.getenv("NVIDIA_API_KEYS"),
        os.getenv("NVIDIA_NIM_API_KEYS"),
        os.getenv("NVIDIA_API_KEY"),
        os.getenv("NVIDIA_NIM_API_KEY"),
        *_PROVIDER_KEY_FILE.get("nvidia", ()),
    )
    nvidia_model: str = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
    nvidia_api_base_url: str = os.getenv("NVIDIA_API_BASE_URL", "https://integrate.api.nvidia.com/v1")
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
    newsapi_key: str | None = os.getenv("NEWSAPI_KEY")
    newsapi_country: str = os.getenv("NEWSAPI_COUNTRY", os.getenv("AURA_DEFAULT_COUNTRY_CODE", "IN")).lower()
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
