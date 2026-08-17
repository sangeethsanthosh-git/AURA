"""Fallback execution helpers for SmartRouter handlers."""

from __future__ import annotations

import logging
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)


class FallbackManager:
    """Runs provider attempts in order and never exposes stack traces."""

    def run(self, attempts: list[tuple[str, Callable[[], dict[str, Any]]]]) -> dict[str, Any]:
        last_response: dict[str, Any] | None = None
        for provider, attempt in attempts:
            try:
                response = attempt()
            except Exception as exc:
                LOGGER.exception("Fallback attempt crashed. provider=%s", provider)
                last_response = {
                    "ok": False,
                    "provider": provider,
                    "action": "fallback",
                    "message": None,
                    "data": {},
                    "error": {"message": "Provider failed.", "details": None, "status_code": None},
                }
                continue
            last_response = response
            if response.get("ok"):
                return response
            LOGGER.warning("Provider failed. provider=%s error=%s", provider, (response.get("error") or {}).get("message"))
        return last_response or {"ok": False, "provider": "fallback", "action": "run", "data": {}, "message": None, "error": {"message": "No provider attempts configured."}}
