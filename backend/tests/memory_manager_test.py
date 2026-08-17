"""Regression tests for the production MemoryManager."""

from __future__ import annotations

import tempfile
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.memory.memory_manager import MemoryManager


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        memory_path = Path(tmp) / "memory.json"
        manager = MemoryManager(path=memory_path)

        checks = [
            ("My name is Sangeeth.", "Nice to meet you, Sangeeth."),
            ("Who am I?", "Your name is Sangeeth."),
            ("I am studying MCA.", "studying MCA"),
            ("What am I studying?", "You're studying MCA."),
            ("I am a software engineer.", "software engineer"),
            ("What do I do?", "You're a software engineer."),
            ("I work at Google.", "work at Google"),
            ("I live in Kerala.", "from Kerala"),
            ("I am 22 years old.", "you're 22"),
            ("I know Python.", "you know Python"),
            ("I know Java.", "you know Java"),
            ("What languages do I know?", "Python and Java"),
            ("My favorite language is Python.", "favorite language is Python"),
            ("My favorite language is Java.", "favorite language is Java"),
            ("My goal is to build AURA.", "build AURA"),
        ]

        for prompt, expected in checks:
            response = manager.handle(prompt)
            message = str(response.get("message", ""))
            if expected.lower() not in message.lower():
                print(f"FAIL {prompt!r}: expected {expected!r}, got {message!r}")
                failures += 1

        if manager.data.profile.education != "MCA":
            print(f"FAIL education stored as {manager.data.profile.education!r}")
            failures += 1
        if manager.data.profile.occupation.lower() != "software engineer":
            print(f"FAIL occupation stored as {manager.data.profile.occupation!r}")
            failures += 1
        if manager.data.preferences.favorite_language != "Java":
            print(f"FAIL favorite language did not update: {manager.data.preferences.favorite_language!r}")
            failures += 1
        if manager.data.skills != ["Python", "Java"]:
            print(f"FAIL skills list incorrect: {manager.data.skills!r}")
            failures += 1

        forgotten = manager.handle("Forget my skills.")
        if "forgotten" not in str(forgotten.get("message", "")).lower() or manager.data.skills:
            print("FAIL forget skills did not clear the list")
            failures += 1

        reloaded = MemoryManager(path=memory_path)
        if reloaded.data.profile.name != "Sangeeth":
            print("FAIL persisted memory did not reload")
            failures += 1

    if failures:
        return 1
    print("PASS memory manager natural structured behavior")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
