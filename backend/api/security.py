"""Authentication primitives using only the Python standard library."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.api.errors import ApiError


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 260_000)
    return "pbkdf2_sha256$260000$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        alg, rounds, salt_b64, digest_b64 = stored.split("$", 3)
        if alg != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def create_token(claims: dict[str, Any], secret: str, expires_delta: timedelta) -> str:
    payload = dict(claims)
    payload["exp"] = int((utcnow() + expires_delta).timestamp())
    payload["jti"] = secrets.token_urlsafe(16)
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = _b64(json.dumps(header, separators=(",", ":")).encode()) + "." + _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return signing_input + "." + _b64(signature)


def decode_token(token: str, secret: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".", 2)
        signing_input = f"{header_b64}.{payload_b64}"
        expected = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
        actual = _unb64(signature_b64)
        if not hmac.compare_digest(actual, expected):
            raise ValueError("bad signature")
        payload = json.loads(_unb64(payload_b64))
        if int(payload.get("exp", 0)) < int(utcnow().timestamp()):
            raise ApiError(401, "TOKEN_EXPIRED", "Authentication token has expired.")
        return payload
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(401, "INVALID_TOKEN", "Authentication token is invalid.") from exc

