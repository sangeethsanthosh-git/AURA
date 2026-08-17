"""Regression tests for deterministic math result integrity."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.router.smart_router import SmartRouter
from backend.router.tool_integrity import validate_math_response
from backend.utils.responses import success_response


class FakeServiceManager:
    def __init__(self, llm_text: str = "587 × 932 = 547084") -> None:
        self.calls: list[tuple[str, str]] = []
        self.llm_text = llm_text

    def ask(self, provider: str, prompt: str, **_: Any) -> dict[str, Any]:
        self.calls.append((provider, prompt))
        return success_response("ollama", "chat", {"content": self.llm_text, "model": "fake"}, self.llm_text)


def assert_math(prompt: str, expected: Any) -> int:
    manager = FakeServiceManager()
    response = SmartRouter(service_manager=manager).ask(prompt)
    result = response.get("data", {}).get("result")
    if result != expected:
        print(f"FAIL {prompt!r}: got {result!r}, expected {expected!r}")
        return 1
    if manager.calls:
        print(f"FAIL {prompt!r}: direct math unexpectedly used LLM")
        return 1
    return 0


def main() -> int:
    failures = 0
    failures += assert_math("587 × 932", 547084)
    failures += assert_math("123 + 456", 579)
    failures += assert_math("100 / 4", 25)
    failures += assert_math("2^10", 1024)
    failures += assert_math("10 × 20", 200)

    direct = SmartRouter(service_manager=FakeServiceManager()).ask("10 × 20")
    route = direct.get("route", {})
    if route.get("execution_source") != "Python Math Engine" or route.get("llm_provider") is not None:
        print(f"FAIL metadata: {route}")
        failures += 1

    explanation_manager = FakeServiceManager("Use place values; the verified result is 547084.")
    explanation = SmartRouter(service_manager=explanation_manager).ask("Explain how to calculate 587 × 932.")
    if explanation.get("data", {}).get("result") != 547084 or not explanation_manager.calls:
        print("FAIL explanation did not preserve math result or use LLM")
        failures += 1
    if "549964" in str(explanation.get("message")):
        print("FAIL explanation contains contradictory result")
        failures += 1

    bad_manager = FakeServiceManager("587 × 932 = 549964")
    bad = SmartRouter(service_manager=bad_manager).ask("Explain how to calculate 587 × 932.")
    if "549964" in str(bad.get("message")) or bad.get("integrity_check") != "REPLACED_LLM_OUTPUT":
        print(f"FAIL incorrect LLM output was not rejected: {bad.get('message')}")
        failures += 1

    if validate_math_response(547084, "587 × 932 = 549964"):
        print("FAIL validator accepted contradictory math output")
        failures += 1

    if failures:
        return 1
    print("PASS deterministic math integrity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
