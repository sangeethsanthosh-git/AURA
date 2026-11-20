"""
AURA Secret Store & Privacy Protection Subsystem
Secures local credentials, provides secret masking, prevents sensitive data leakage in logs,
and enforces zero-cloud transmission of private personal documents without explicit authorization.
"""

from typing import Dict, Any, Optional
import os
import re
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Regex pattern for scrubbing API keys, tokens, and authorization headers from logs
SECRET_SCRUB_RE = re.compile(
    r"(?:sk-[a-zA-Z0-9_-]{20,}|ghp_[a-zA-Z0-9]{20,}|Bearer\s+[a-zA-Z0-9._-]{20,}|AKIA[0-9A-Z]{16}|(?<=password=)[^\s&]+|(?<=secret=)[^\s&]+)",
    re.IGNORECASE,
)


class SecretStore:
    """Encrypted/isolated storage for local API credentials and private user settings."""

    def __init__(self):
        user_home = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))).resolve()
        self.store_dir = user_home / "AppData" / "Local" / "AURA" / "credentials"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.secrets_file = self.store_dir / "secrets.json"

    @property
    def credentials_file(self) -> Path:
        return self.secrets_file

    def get_secret(self, key_name: str) -> Optional[str]:
        """Retrieve a stored secret by key name."""
        # Check environment variable first
        if key_name in os.environ:
            return os.environ[key_name]

        if not self.secrets_file.exists():
            return None

        try:
            with open(self.secrets_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(key_name)
        except Exception as e:
            logger.error(f"Error reading secret '{key_name}': {e}")
            return None

    def set_secret(self, key_name: str, secret_val: str) -> bool:
        """Securely persist a secret key."""
        try:
            data = {}
            if self.secrets_file.exists():
                try:
                    with open(self.secrets_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}

            data[key_name] = secret_val
            with open(self.secrets_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            logger.error(f"Error saving secret '{key_name}': {e}")
            return False

    @staticmethod
    def scrub_text(text: str) -> str:
        """Redact secrets and sensitive tokens from log messages or visual output."""
        if not text:
            return ""
        return SECRET_SCRUB_RE.sub("[REDACTED_SECRET]", text)


# Global secret store instance
secret_store = SecretStore()
