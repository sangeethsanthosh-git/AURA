"""Reusable scoring helpers for intent classification."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable


def normalize_text(text: str) -> str:
    return " ".join(text.lower().strip().split())


def keyword_score(text: str, keywords: Iterable[str]) -> tuple[float, list[str]]:
    matches = [keyword for keyword in keywords if _contains_keyword(text, keyword)]
    if not matches:
        return 0.0, []
    score = min(0.92, 0.68 + 0.08 * len(matches))
    return score, matches


def _contains_keyword(text: str, keyword: str) -> bool:
    """Match words and phrases without substring false positives."""
    escaped = re.escape(keyword.lower())
    if re.search(r"\w", keyword):
        return bool(re.search(rf"(?<!\w){escaped}(?!\w)", text))
    return keyword in text


def pattern_score(text: str, patterns: Iterable[re.Pattern[str]]) -> tuple[float, str | None]:
    for pattern in patterns:
        if pattern.search(text):
            return 0.94, pattern.pattern
    return 0.0, None


def semantic_score(text: str, examples: Iterable[str]) -> tuple[float, str | None]:
    best = 0.0
    best_example: str | None = None
    for example in examples:
        score = SequenceMatcher(None, text, example).ratio()
        if score > best:
            best = score
            best_example = example
    if best < 0.62:
        return 0.0, None
    return round(min(0.89, best), 2), best_example


def looks_like_math(text: str) -> bool:
    if re.search(r"\d+(?:\.\d+)?\s*%\s+of\s+\d+(?:\.\d+)?", text):
        return True
    math_chars = r"\d\s+\-*/xX\u00d7Ã—\u00f7Ã·%^().=?!"
    if re.fullmatch(rf"(what is|calculate|solve|compute)\s+[{math_chars}]+", text):
        return True
    if re.search(rf"\d\s*[+\-*/xX\u00d7Ã—\u00f7Ã·%^]\s*\d", text):
        return True
    return bool(re.fullmatch(rf"[{math_chars}]+", text))
