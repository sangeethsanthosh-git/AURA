"""Lightweight Malayalam, Manglish, and mixed-language detection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class LanguageRoute(StrEnum):
    ENGLISH = "english"
    MALAYALAM = "malayalam"
    MIXED = "mixed"
    OTHER = "other"


@dataclass(frozen=True)
class DetectedLanguage:
    route: LanguageRoute
    code: str
    confidence: float
    reason: str


class LanguageDetector:
    MALAYALAM_RE = re.compile(r"[\u0D00-\u0D7F]")
    MANGLISH_TERMS = {
        "entha", "engane", "cheyyunne", "cheyyamo", "pattumo", "aanu", "alle",
        "njan", "innu", "ivide", "undu", "onn", "nokki", "pokam", "venam",
        "sughamano", "machane", "pwoli", "ithu", "ee", "oru",
    }
    ENGLISH_TECH_TERMS = {"python", "rag", "code", "file", "weather", "local", "knowledge", "api", "chrome"}

    def detect(self, text: str) -> DetectedLanguage:
        lowered = text.lower()
        has_ml = bool(self.MALAYALAM_RE.search(text))
        tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9+-]*", lowered))
        manglish_hits = tokens & self.MANGLISH_TERMS
        tech_hits = tokens & self.ENGLISH_TECH_TERMS

        if has_ml and tech_hits:
            return DetectedLanguage(LanguageRoute.MIXED, "mixed", 0.9, "Malayalam script with English technical terms.")
        if has_ml:
            return DetectedLanguage(LanguageRoute.MALAYALAM, "ml", 0.9, "Malayalam Unicode detected.")
        if manglish_hits and tech_hits:
            return DetectedLanguage(LanguageRoute.MIXED, "mixed", 0.82, "Manglish with English technical terms.")
        if manglish_hits:
            return DetectedLanguage(LanguageRoute.MIXED, "mixed", 0.74, "Manglish-style Malayalam words detected.")
        if tokens:
            return DetectedLanguage(LanguageRoute.ENGLISH, "en", 0.75, "Latin-script English/default text.")
        return DetectedLanguage(LanguageRoute.OTHER, "other", 0.2, "No reliable language signal.")
