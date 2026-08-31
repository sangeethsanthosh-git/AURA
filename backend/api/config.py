"""Configuration for the AURA REST API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from backend.config.config import BASE_DIR, _load_dotenv

_load_dotenv()


@dataclass(frozen=True)
class ApiSettings:
    host: str = os.getenv("AURA_API_HOST", "127.0.0.1")
    port: int = int(os.getenv("AURA_API_PORT", "8765"))
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'aura.sqlite3'}")
    access_token_secret: str = os.getenv("JWT_SECRET", "change-me-in-production")
    refresh_token_secret: str = os.getenv("JWT_REFRESH_SECRET", "change-me-refresh-in-production")
    access_token_minutes: int = int(os.getenv("AURA_ACCESS_TOKEN_MINUTES", "30"))
    refresh_token_days: int = int(os.getenv("AURA_REFRESH_TOKEN_DAYS", "14"))
    cors_origin: str = os.getenv("CORS_ORIGIN", "http://127.0.0.1:5173")
    max_body_bytes: int = int(os.getenv("AURA_MAX_BODY_BYTES", "1048576"))
    rate_limit_per_minute: int = int(os.getenv("AURA_RATE_LIMIT_PER_MINUTE", "60"))
    debug: bool = os.getenv("DEBUG", os.getenv("AURA_DEBUG", "false")).lower() in {"1", "true", "yes", "on"}

    @property
    def sqlite_path(self) -> Path:
        if not self.database_url.startswith("sqlite:///"):
            raise ValueError("Only sqlite:/// DATABASE_URL values are supported by the stdlib API server.")
        return Path(self.database_url.removeprefix("sqlite:///")).expanduser().resolve()


settings = ApiSettings()

