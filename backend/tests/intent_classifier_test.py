"""Regression tests for the modular confidence-based IntentClassifier."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.router.intent_classifier import IntentClassifier
from backend.router.intent_types import Intent


def main() -> int:
    classifier = IntentClassifier()
    cases = [
        ("My name is Sangeeth.", Intent.MEMORY, "MemoryManager"),
        ("Who am I?", Intent.MEMORY, "MemoryManager"),
        ("Write Python code.", Intent.PROGRAMMING, "Groq"),
        ("Explain FastAPI.", Intent.PROGRAMMING, "Groq"),
        ("Who is Alan Turing?", Intent.GENERAL_KNOWLEDGE, "Wikipedia"),
        ("Weather in Kochi.", Intent.WEATHER, "Open-Meteo"),
        ("Locate Delhi.", Intent.MAPS, "OpenStreetMap"),
        ("Translate Good Morning to Malayalam.", Intent.TRANSLATION, "Hugging Face"),
        ("What is 587 × 932?", Intent.MATHEMATICS, "Local Math Engine"),
        ("If all cats are animals...", Intent.REASONING, "Groq"),
        ("Current stock price.", Intent.FINANCE, "Finance service is not installed."),
        ("Read the Malayalam text.", Intent.VISION, "AURA EYES"),
        ("What's written here?", Intent.VISION, "AURA EYES"),
        ("Which application is open?", Intent.VISION, "AURA EYES"),
        ("Where is the plus button?", Intent.VISION, "AURA EYES"),
        ("What is my project?", Intent.GENERAL_KNOWLEDGE, "Wikipedia"),
    ]

    failures = 0
    for prompt, expected_intent, expected_provider in cases:
        result = classifier.classify(prompt)
        if result.intent != expected_intent or result.provider != expected_provider:
            print(
                f"FAIL {prompt!r}: got {result.intent.value}/{result.provider} "
                f"expected {expected_intent.value}/{expected_provider}. reason={result.reason}"
            )
            failures += 1
        if result.intent != Intent.UNKNOWN and result.confidence < 0.60:
            print(f"FAIL {prompt!r}: confidence too low {result.confidence}")
            failures += 1

    if failures:
        return 1
    print("PASS modular intent classifier behavior")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
