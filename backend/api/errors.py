"""API error classes and response builders."""

from __future__ import annotations

from typing import Any


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def success(data: Any, message: str = "Operation completed successfully") -> dict[str, Any]:
    return {"success": True, "data": data, "message": message}


def failure(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    return {"success": False, "error": {"code": code, "message": message, "details": details or []}}

