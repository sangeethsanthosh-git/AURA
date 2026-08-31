"""Small request validators for the REST API."""

from __future__ import annotations

import re
from typing import Any

from backend.api.errors import ApiError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def require_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ApiError(400, "BAD_REQUEST", "Request body must be a JSON object.")
    return value


def require_string(data: dict[str, Any], key: str, *, min_len: int = 1, max_len: int = 4000) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise ApiError(422, "VALIDATION_ERROR", f"{key} must be a string.")
    value = value.strip()
    if len(value) < min_len or len(value) > max_len:
        raise ApiError(422, "VALIDATION_ERROR", f"{key} must be between {min_len} and {max_len} characters.")
    return value


def validate_email(email: str) -> str:
    clean = email.strip().lower()
    if len(clean) > 254 or not EMAIL_RE.match(clean):
        raise ApiError(422, "VALIDATION_ERROR", "email must be a valid email address.")
    return clean


def validate_password(password: str) -> str:
    if len(password) < 8 or len(password) > 128:
        raise ApiError(422, "VALIDATION_ERROR", "password must be between 8 and 128 characters.")
    if password.isalpha() or password.isdigit():
        raise ApiError(422, "VALIDATION_ERROR", "password must contain a mix of character types.")
    return password

