"""Structured response helpers for AURA services."""

from __future__ import annotations

from typing import Any


def success_response(
    provider: str,
    action: str,
    data: dict[str, Any],
    message: str | None = None,
) -> dict[str, Any]:
    """Create the common success shape returned by every service."""
    return {
        "ok": True,
        "provider": provider,
        "action": action,
        "message": message,
        "data": data,
        "error": None,
    }


def error_response(
    provider: str,
    action: str,
    error: str,
    status_code: int | None = None,
    details: Any | None = None,
) -> dict[str, Any]:
    """Create the common error shape returned by every service."""
    return {
        "ok": False,
        "provider": provider,
        "action": action,
        "message": None,
        "data": {},
        "error": {
            "message": error,
            "status_code": status_code,
            "details": details,
        },
    }
