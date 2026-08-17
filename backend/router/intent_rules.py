"""Intent rule registry for AURA.

Adding a new intent should mean registering one more ``IntentRule`` rather than
editing a long classifier if/else chain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from backend.router.classifier_utils import keyword_score, looks_like_math, pattern_score, semantic_score
from backend.router.intent_types import Intent


@dataclass(frozen=True)
class RuleMatch:
    intent: Intent
    confidence: float
    provider: str
    reason: str
    priority: int


@dataclass(frozen=True)
class IntentRule:
    intent: Intent
    provider: str
    priority: int
    keywords: tuple[str, ...] = ()
    patterns: tuple[re.Pattern[str], ...] = ()
    examples: tuple[str, ...] = ()
    custom: Callable[[str], tuple[float, str] | None] | None = None

    def evaluate(self, text: str) -> RuleMatch | None:
        candidates: list[tuple[float, str]] = []
        if self.custom:
            custom_match = self.custom(text)
            if custom_match:
                candidates.append(custom_match)
        p_score, pattern = pattern_score(text, self.patterns)
        if pattern:
            candidates.append((p_score, "Detected intent-specific sentence pattern."))
        k_score, matches = keyword_score(text, self.keywords)
        if matches:
            candidates.append((k_score, f"Detected keywords: {', '.join(matches[:4])}."))
        s_score, example = semantic_score(text, self.examples)
        if example:
            candidates.append((s_score, f"Similar to example: {example}."))
        if not candidates:
            return None
        confidence, reason = max(candidates, key=lambda item: item[0])
        return RuleMatch(self.intent, confidence, self.provider, reason, self.priority)


def _math_custom(text: str) -> tuple[float, str] | None:
    if looks_like_math(text):
        return 0.98, "Detected mathematical expression."
    return None


def _weather_custom(text: str) -> tuple[float, str] | None:
    travel_terms = ("travel", "train", "route", "ticket", "visit", "tour")
    weather_terms = ("weather", "temperature", "rain", "forecast", "humidity")
    if any(term in text for term in weather_terms) and not any(term in text for term in travel_terms):
        return 0.95, "Detected live weather terminology."
    return None


INTENT_RULES: tuple[IntentRule, ...] = (
    IntentRule(
        Intent.MEMORY,
        "MemoryManager",
        100,
        keywords=("my name is", "what is my name", "who am i", "remember", "forget", "tell me about me", "do you remember me", "what do you know about me"),
        patterns=(
            re.compile(r"\b(my name is|what is my name|who am i|remember|forget|tell me about me|what do you know about me)\b"),
        ),
    ),
    IntentRule(
        Intent.SYSTEM_COMMANDS,
        "System",
        95,
        patterns=(re.compile(r"^(exit|quit|help|version)\b|^(clear|reset|restart)$"),),
        examples=("help", "version", "restart"),
    ),
    IntentRule(
        Intent.MATHEMATICS,
        "Local Math Engine",
        90,
        keywords=("gcd", "lcm", "factorial", "percentage", "square root", "sqrt", "quadratic", "prime", "modulus"),
        examples=("587 × 932", "2^10", "find gcd", "quadratic equation"),
        custom=_math_custom,
    ),
    IntentRule(
        Intent.REASONING,
        "Groq",
        80,
        keywords=("if all", "logic puzzle", "train puzzle", "word problem", "reasoning", "riddle"),
        examples=("if all cats are animals", "solve this train puzzle"),
    ),
    IntentRule(
        Intent.PROGRAMMING,
        "Groq",
        75,
        keywords=("code", "python", "java", "fastapi", "rest api", "react hooks", "javascript", "typescript", "inheritance", "debug", "function", "class"),
        examples=("write python code", "explain fastapi", "build rest api", "java inheritance"),
    ),
    IntentRule(
        Intent.TRANSLATION,
        "Hugging Face",
        70,
        keywords=("translate", "translation", "convert english", "speak in", "meaning in"),
        examples=("translate good morning to malayalam", "convert english to hindi"),
    ),
    IntentRule(
        Intent.FINANCE,
        "Finance service is not installed.",
        68,
        keywords=("stock price", "bitcoin", "gold rate", "currency", "sensex", "nifty", "current market"),
        examples=("current stock price", "bitcoin price", "gold rate today"),
    ),
    IntentRule(
        Intent.WEATHER,
        "Open-Meteo",
        65,
        keywords=("weather", "temperature", "rain tomorrow", "current weather", "forecast", "humidity"),
        examples=("weather in kochi", "temperature today", "rain tomorrow"),
        custom=_weather_custom,
    ),
    IntentRule(
        Intent.MAPS,
        "OpenStreetMap",
        60,
        keywords=("locate", "coordinates", "nearest airport", "find delhi", "map", "address of"),
        examples=("locate kochi", "coordinates of delhi", "nearest airport"),
    ),
    IntentRule(
        Intent.FILE_OPERATIONS,
        "RAG",
        82,
        keywords=("analyze file", "analyze this", "read document", "summarize pdf", "summarize document", "explain this document", "clear document context"),
        patterns=(re.compile(r"\b(analyze|summarize|explain|read)\b.+\.(txt|md|pdf)\b"),),
        examples=("summarize pdf", "read this document", "analyze report.pdf"),
    ),
    IntentRule(
        Intent.RAG,
        "RAG",
        78,
        keywords=("rag", "knowledge base", "my documents", "from my files", "local knowledge", "add this document", "add this pdf", "remember this document", "search my knowledge", "what does my document"),
        examples=("answer from my documents", "search my knowledge base", "what does my project documentation say"),
    ),
    IntentRule(
        Intent.GENERAL_KNOWLEDGE,
        "Wikipedia",
        40,
        patterns=(re.compile(r"^(who|what|when|where) (is|was|are|were)\b"),),
        keywords=("history", "science", "country", "countries", "organization", "event"),
        examples=("who is alan turing", "history of india", "what is artificial intelligence"),
    ),
    IntentRule(
        Intent.CONVERSATION,
        "Ollama",
        10,
        keywords=("hello", "hi", "how are you", "tell me a joke", "thanks"),
        patterns=(re.compile(r"\b(tell me a joke|hello|hi|how are you|thanks)\b"),),
        examples=("hello", "how are you", "tell me a joke"),
    ),
)
