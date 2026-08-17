"""Lightweight integrity helpers for authoritative tool results."""

from __future__ import annotations

import re
from typing import Any


def deterministic_tool_result(
    tool_name: str,
    source: str,
    data: dict[str, Any],
    execution_time: float | None = None,
) -> dict[str, Any]:
    """Return metadata that marks tool data as authoritative."""
    return {
        "success": True,
        "tool_name": tool_name,
        "source": source,
        "authoritative": True,
        "data": data,
        "execution_time": execution_time,
        "error": None,
    }


def validate_math_response(authoritative_result: Any, final_text: str) -> bool:
    """Reject LLM text that contains numbers but omits the verified result."""
    expected = _normalize_number(authoritative_result)
    numbers = {_normalize_number(item) for item in re.findall(r"-?\d+(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?", final_text)}
    if not numbers:
        return True
    return expected in numbers


def safe_math_response(expression: str, authoritative_result: Any) -> str:
    value = authoritative_result
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    formatted = f"{value:,}" if isinstance(value, int) else str(value)
    return f"{expression} = {formatted}"


def _normalize_number(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).replace(",", "")
