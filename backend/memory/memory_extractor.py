"""Rule-based, extensible information extraction for AURA memory."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from backend.memory.memory_models import ExtractionResult
from backend.memory.memory_utils import clean_age, clean_value, normalize_text

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExtractionRule:
    category: str
    field: str
    pattern: re.Pattern[str]
    confidence: float
    is_list: bool = False
    cleaner: str = "default"


class MemoryExtractor:
    """Extracts structured user memories from natural language."""

    def __init__(self) -> None:
        self.rules = (
            ExtractionRule("profile", "name", re.compile(r"\bmy name is\s+(.+)$", re.IGNORECASE), 0.98),
            ExtractionRule("profile", "name", re.compile(r"\bcall me\s+(.+)$", re.IGNORECASE), 0.95),
            ExtractionRule("profile", "name", re.compile(r"^i(?: am|'m)\s+([A-Z][A-Za-z .'-]{1,40})[.!?]*$"), 0.86, cleaner="name"),
            ExtractionRule("profile", "age", re.compile(r"\bi(?: am|'m)\s+(\d{1,3})(?:\s+years?\s+old)?[.!?]*$", re.IGNORECASE), 0.94, cleaner="age"),
            ExtractionRule("profile", "education", re.compile(r"\bi study\s+(.+)$", re.IGNORECASE), 0.96),
            ExtractionRule("profile", "education", re.compile(r"\bi(?: am|'m)\s+studying\s+(.+)$", re.IGNORECASE), 0.97),
            ExtractionRule("profile", "education", re.compile(r"\bi(?: am|'m)\s+an?\s+(.+?)\s+student\b", re.IGNORECASE), 0.96),
            ExtractionRule("profile", "education", re.compile(r"\bi completed\s+(.+)$", re.IGNORECASE), 0.93),
            ExtractionRule("profile", "company", re.compile(r"\bi work (?:at|for)\s+(.+)$", re.IGNORECASE), 0.95),
            ExtractionRule("profile", "location", re.compile(r"\bi live in\s+(.+)$", re.IGNORECASE), 0.95),
            ExtractionRule("profile", "location", re.compile(r"\bi(?: am|'m) from\s+(.+)$", re.IGNORECASE), 0.93),
            ExtractionRule("profile", "occupation", re.compile(r"\bi work as\s+an?\s+(.+)$", re.IGNORECASE), 0.94),
            ExtractionRule("profile", "occupation", re.compile(r"\bi(?: am|'m)\s+an?\s+(.+)$", re.IGNORECASE), 0.78),
            ExtractionRule("preferences", "favorite_language", re.compile(r"\bmy favou?rite (?:programming )?language is\s+(.+)$", re.IGNORECASE), 0.96),
            ExtractionRule("preferences", "favorite_language", re.compile(r"\bmy favou?rite language is\s+(.+)$", re.IGNORECASE), 0.96),
            ExtractionRule("preferences", "favorite_language", re.compile(r"\bi (?:now |currently )?prefer\s+(python|java|javascript|typescript|c\+\+|c#|go|rust|php|ruby|kotlin|swift|r)\b", re.IGNORECASE), 0.92),
            ExtractionRule("preferences", "preferred_ai", re.compile(r"\bi (?:like|prefer)\s+(ollama|groq|hugging face|chatgpt|openai|claude|gemini)\b", re.IGNORECASE), 0.88),
            ExtractionRule("preferences", "operating_system", re.compile(r"\bi prefer\s+(linux|windows|macos|mac os)\b", re.IGNORECASE), 0.90),
            ExtractionRule("preferences", "preferred_ai", re.compile(r"\bi (?:now |currently )?prefer\s+(.+)$", re.IGNORECASE), 0.87),
            ExtractionRule("skills", "skills", re.compile(r"\bi know\s+(.+)$", re.IGNORECASE), 0.93, is_list=True),
            ExtractionRule("skills", "skills", re.compile(r"\bi use\s+(.+)$", re.IGNORECASE), 0.84, is_list=True),
            ExtractionRule("goals", "goals", re.compile(r"\bmy goal is\s+(.+)$", re.IGNORECASE), 0.95, is_list=True, cleaner="goal"),
            ExtractionRule("goals", "goals", re.compile(r"\bmy goal is to\s+(.+)$", re.IGNORECASE), 0.95, is_list=True),
            ExtractionRule("goals", "goals", re.compile(r"\bi want to\s+(.+)$", re.IGNORECASE), 0.88, is_list=True),
            ExtractionRule("projects", "projects", re.compile(r"\bmy project is\s+(.+)$", re.IGNORECASE), 0.90, is_list=True),
            ExtractionRule("projects", "projects", re.compile(r"\bproject name is\s+(.+)$", re.IGNORECASE), 0.90, is_list=True),
        )

    def extract(self, text: str) -> ExtractionResult | None:
        source = re.sub(r"^remember(?: that| this)?\s+", "", normalize_text(text), flags=re.IGNORECASE).strip()
        for rule in self.rules:
            match = rule.pattern.search(source)
            if not match:
                continue
            value = self._clean(match.group(1), rule.cleaner)
            if not value or self._looks_like_question(value):
                continue
            result = ExtractionResult(rule.category, rule.field, value, rule.confidence, rule.is_list)
            LOGGER.info(
                "Extraction Result: Detected Entity=%s Detected Category=%s Confidence Score=%.2f Value=%s",
                result.field,
                result.category,
                result.confidence,
                result.value,
            )
            return result
        return None

    @staticmethod
    def _clean(value: str, cleaner: str) -> str:
        if cleaner == "age":
            return clean_age(value)
        if cleaner == "name":
            return value.strip(" .!?")
        if cleaner == "goal":
            value = clean_value(value)
            return value[3:] if value.lower().startswith("to ") else value
        value = clean_value(value)
        if value.lower().endswith(" student"):
            value = value[:-8].strip()
        if value.lower().startswith(("a ", "an ")):
            value = value.split(" ", 1)[1].strip()
        return value

    @staticmethod
    def _looks_like_question(value: str) -> bool:
        return value.lower().startswith(("what ", "who ", "where ", "when ", "why ", "how "))
