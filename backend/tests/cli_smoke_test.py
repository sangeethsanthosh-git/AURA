"""Simple CLI smoke tests for AURA smart routing and service integrations.

Run with:
    python backend/tests/cli_smoke_test.py

The online LLM providers are considered healthy when they either return a
successful response or return a structured error. This keeps the default
regression suite independent of paid API availability. Free web services should
return successful responses when the network is available.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.router.intent_classifier import IntentClassifier
from backend.router.service_manager import ServiceManager
from backend.router.smart_router import SmartRouter


def main() -> int:
    manager = ServiceManager()
    router = SmartRouter(manager)
    classifier = IntentClassifier()

    intent_checks = [
        ("What is the weather in Kochi?", "Weather"),
        ("Locate Taj Mahal", "Maps"),
        ("Who is Alan Turing?", "General Knowledge"),
        ("Write Python code to reverse a string", "Programming"),
        ("Translate hello to French", "Translation"),
        ("Tell me a joke", "Conversation"),
    ]

    failures = 0
    for prompt, expected_intent in intent_checks:
        result = classifier.classify(prompt)
        passed = result.intent.value == expected_intent
        status = "PASS" if passed else "FAIL"
        print(f"{status} intent: {prompt} -> {result.intent.value}")
        if not passed:
            failures += 1

    direct_checks = [
        ("groq", "hello", {}),
        ("huggingface", "hello", {}),
        ("wikipedia", "Alan Turing", {"action": "summary"}),
        ("weather", "Kochi", {}),
        ("maps", "Kochi", {}),
    ]

    for provider, prompt, kwargs in direct_checks:
        response = manager.ask(provider, prompt, **kwargs)
        ok = response["ok"]
        error = response.get("error") or {}
        graceful_provider_error = provider in {"groq", "huggingface"} and bool(error.get("message"))
        passed = ok or graceful_provider_error
        status = "PASS" if passed else "FAIL"
        print(f"{status} {provider}: {response['action']}")
        if not passed:
            failures += 1
            print(f"  {error.get('message', 'Unknown error')}")

    route_checks = [
        ("What is the weather in Kochi?", "Weather", "Open-Meteo"),
        ("Locate Taj Mahal", "Maps", "OpenStreetMap"),
        ("Who is Alan Turing?", "General Knowledge", "Wikipedia"),
    ]

    for prompt, expected_intent, expected_provider in route_checks:
        response = router.ask(prompt)
        route = response.get("route", {})
        passed = (
            response.get("ok")
            and route.get("intent") == expected_intent
            and route.get("provider") == expected_provider
        )
        status = "PASS" if passed else "FAIL"
        print(
            f"{status} route: {prompt} -> "
            f"{route.get('intent')} / {route.get('provider')}"
        )
        if not passed:
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
