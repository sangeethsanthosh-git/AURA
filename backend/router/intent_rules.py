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


def _web_current_custom(text: str) -> tuple[float, str] | None:
    current_terms = (
        "latest", "recent", "today", "currently", "current", "this week", "this month",
        "new release", "latest research", "recent papers", "happened today", "news",
    )
    specialized_terms = (
        "weather", "temperature", "rain", "forecast", "locate", "coordinates", "map",
        "stock", "bitcoin", "gold rate", "currency", "sensex", "nifty", "market",
    )
    local_terms = ("my document", "my documents", "local knowledge", "knowledge base", "from my files")
    if any(term in text for term in current_terms) and not any(term in text for term in specialized_terms + local_terms):
        return 0.93, "Detected current-information web terminology."
    return None


INTENT_RULES: tuple[IntentRule, ...] = (
    IntentRule(
        Intent.VISION,
        "AURA EYES",
        99,
        keywords=(
            "look at my screen", "what is on my screen", "what am i looking at",
            "read what's on my screen", "read what is on my screen", "explain this error",
            "look at this error", "what application am i looking at", "did chrome open",
            "did the search work",
        ),
        patterns=(
            re.compile(r"\b(look at|inspect|see|read|analyze)\b.*\b(screen|this error|what'?s shown)\b"),
            re.compile(r"^what (is|am i) .*\b(screen|looking at)\b"),
            re.compile(r"^did .+\b(open|work|appear|show up)\??$"),
        ),
        examples=("look at my screen", "what is on my screen", "explain this error", "read what's on my screen"),
    ),
    IntentRule(
        Intent.COMPUTER_ACTIONS,
        "AURA HANDS",
        98,
        keywords=(
            "open chrome", "open youtube", "open chatgpt", "open github", "open downloads",
            "open documents", "search google", "search youtube", "create folder",
            "rename file", "copy file", "move file", "launch calculator", "open calculator",
            "play spotify", "play music", "pause music", "stop music", "next track",
            "previous track", "close chrome", "close vscode", "focus chrome", "click settings",
            "type hello", "press enter", "scroll down", "confirm", "proceed", "cancel action", "abort",
        ),
        patterns=(
            re.compile(r"^(open|launch|start)\s+.+"),
            re.compile(r"^(play|pause|stop|next|previous|resume)(\s+.+)?$"),
            re.compile(r"^(close|quit|focus|switch to)\s+.+"),
            re.compile(r"^(click|double click|scroll|press|type|write)\s+.+"),
            re.compile(r"^search(\s+(google|youtube|web))?\s+for\s+.+"),
            re.compile(r"^create\s+(a\s+)?folder\b.+"),
            re.compile(r"^(rename|copy|move)\s+(file\s+)?.+\s+to\s+.+"),
            re.compile(r"^(yes|confirm|proceed|do it|go ahead|no|cancel|stop|abort)$"),
        ),
        examples=("open chrome", "open youtube", "search google for python tutorials", "create a folder called Research"),
    ),
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
        Intent.WEB_INTELLIGENCE,
        "Web Intelligence",
        99,
        keywords=(
            "latest ai news", "latest news", "recent developments", "current python release",
            "latest python release", "happened today", "latest research", "recent papers",
            "current version", "new release", "currently", "today in",
        ),
        patterns=(
            re.compile(r"^(?!.*\b(weather|temperature|rain|forecast|stock|bitcoin|gold rate|currency|sensex|nifty|market|map|coordinates)\b).*\b(latest|recent|current|today|this week|this month|new release|happened today)\b"),
            re.compile(r"^(?!.*\b(weather|temperature|rain|forecast|stock|bitcoin|gold rate|currency|sensex|nifty|market|map|coordinates)\b).*\b(search|find)\b.*\b(recent|latest|papers|research|news)\b"),
        ),
        examples=("latest AI news", "what happened today in NVIDIA", "current Python release", "recent papers about RAG"),
        custom=_web_current_custom,
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
