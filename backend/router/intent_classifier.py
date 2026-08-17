"""Confidence-based modular intent classifier for AURA."""

from __future__ import annotations

import logging
import re
import time

from backend.router.intent_rules import INTENT_RULES, RuleMatch
from backend.router.intent_types import Intent, IntentResult

LOGGER = logging.getLogger(__name__)


class IntentClassifier:
    """Classifies each request into one primary intent.

    Rules are registered in ``intent_rules.py``. The classifier evaluates every
    rule, ranks by priority and confidence, and falls back to Unknown when
    confidence is below the production threshold.
    """

    MIN_CONFIDENCE = 0.60
    EXPLANATION_TERMS = {"explain", "why", "how", "describe", "detail", "briefly"}

    def classify(self, user_input: str) -> IntentResult:
        """Return intent, confidence, provider, reason, and cleaned query."""
        started = time.perf_counter()
        normalized = self._normalize(user_input)
        matches = [match for rule in INTENT_RULES if (match := rule.evaluate(normalized))]

        if not matches:
            result = IntentResult(
                Intent.UNKNOWN,
                0.0,
                user_input,
                "Ollama",
                "No classifier rule exceeded the minimum confidence.",
            )
            self._log(result, started)
            return result

        selected = max(matches, key=lambda match: (match.priority, match.confidence))
        if selected.confidence < self.MIN_CONFIDENCE:
            result = IntentResult(
                Intent.UNKNOWN,
                selected.confidence,
                user_input,
                "Ollama",
                f"Best match below threshold: {selected.reason}",
            )
            self._log(result, started)
            return result

        result = IntentResult(
            selected.intent,
            round(selected.confidence, 2),
            self._clean_query(user_input, selected.intent),
            selected.provider,
            selected.reason,
            needs_explanation=self._needs_explanation(normalized),
        )
        self._log(result, started)
        return result

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.lower().strip().split())

    def _clean_query(self, text: str, intent: Intent) -> str:
        if intent == Intent.WEATHER:
            return self._clean_weather_query(text)
        if intent in {Intent.MAPS, Intent.LOCATION}:
            return self._clean_maps_query(text)
        if intent == Intent.GENERAL_KNOWLEDGE:
            return self._clean_knowledge_query(text)
        return text

    @staticmethod
    def _clean_weather_query(text: str) -> str:
        cleaned = re.sub(
            r"\b(what is|what's|current|today'?s|the|weather|temperature|forecast|in|at|for|will it rain|tomorrow)\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        return " ".join(cleaned.split()).strip(" ?.,!")

    @staticmethod
    def _clean_maps_query(text: str) -> str:
        cleaned = re.sub(
            r"\b(locate|location of|coordinates of|coordinate of|where is|map|address of|find|nearest)\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        return " ".join(cleaned.split()).strip(" ?.,!") or text

    @staticmethod
    def _clean_knowledge_query(text: str) -> str:
        cleaned = re.sub(
            r"\b(who is|who was|what is|what was|tell me about|define|explain)\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        return " ".join(cleaned.split()).rstrip("?") or text

    def _needs_explanation(self, normalized: str) -> bool:
        return any(term in normalized for term in self.EXPLANATION_TERMS)

    @staticmethod
    def _log(result: IntentResult, started: float) -> None:
        LOGGER.info(
            "\n==============================\n"
            "Detected Intent\n%s\n\nConfidence\n%.2f\n\nProvider\n%s\n\nExecution Time\n%.3f sec\n\nReason\n%s\n"
            "==============================",
            result.intent.value,
            result.confidence,
            result.provider,
            time.perf_counter() - started,
            result.reason,
        )


__all__ = ["IntentClassifier", "Intent", "IntentResult", "RuleMatch"]
