"""Regression tests for priority-based SmartRouter behavior."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.router.smart_router import SmartRouter


def main() -> int:
    router = SmartRouter()
    failures = 0

    router.ask("My name is Sangeeth.")
    memory = router.ask("What is my name?")
    if memory.get("route", {}).get("intent") != "Memory" or memory.get("message") != "Your name is Sangeeth.":
        print("FAIL memory question did not use MemoryManager or preserve spelling")
        failures += 1

    math_response = router.ask("587 × 932")
    if math_response.get("route", {}).get("intent") != "Mathematics":
        print("FAIL arithmetic was not classified as Mathematics")
        failures += 1
    if "547084" not in str(math_response.get("message")):
        print("FAIL local math engine returned wrong result")
        failures += 1
    if math_response.get("route", {}).get("provider") == "Wikipedia":
        print("FAIL math routed to Wikipedia")
        failures += 1

    knowledge = router.ask("Who is Alan Turing?")
    if knowledge.get("route", {}).get("intent") != "General Knowledge":
        print("FAIL knowledge question was not classified correctly")
        failures += 1

    if failures:
        return 1
    print("PASS smart router priority behavior")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
