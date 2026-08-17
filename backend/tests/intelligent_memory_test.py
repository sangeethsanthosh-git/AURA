"""Regression tests for intelligent local-first memory decisions."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.memory.daily_memory import DailyMemory
from backend.memory.memory_manager import MemoryManager
from backend.memory.memory_models import MemoryStatus, RetrievalDecision, StorageDecision
from backend.memory.memory_retriever import MemoryRetriever


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manager = MemoryManager(path=root / "memory.json")
        manager.daily_memory = DailyMemory(root / "daily")
        manager.retriever = MemoryRetriever(manager.daily_memory)

        explicit = manager.plan("Remember that I prefer Python.")
        if explicit.storage != StorageDecision.LONG_TERM:
            print("FAIL explicit memory did not choose LONG_TERM storage")
            failures += 1
        response = manager.handle("Remember that I prefer Python.")
        active = [m for m in manager.data.long_term if m.status == MemoryStatus.ACTIVE.value]
        if not response.get("ok") or not active or active[-1].category != "PREFERENCE":
            print("FAIL explicit preference was not stored as long-term PREFERENCE")
            failures += 1
        if manager.data.preferences.favorite_language != "Python":
            print("FAIL explicit programming preference did not update favorite_language")
            failures += 1

        casual = manager.plan("Hello, how are you?")
        if casual.storage == StorageDecision.LONG_TERM:
            print("FAIL casual conversation was promoted to long-term memory")
            failures += 1
        manager.observe_interaction("Hello, how are you?")
        if manager.data.conversation:
            print("FAIL session conversation was persisted to long-term JSON memory")
            failures += 1

        recall = manager.plan("What is my name?")
        if recall.retrieval != RetrievalDecision.LONG_TERM:
            print("FAIL personal fact recall did not choose LONG_TERM retrieval")
            failures += 1

        daily = manager.plan("What were we discussing earlier today?")
        if daily.retrieval != RetrievalDecision.DAILY:
            print("FAIL daily context question did not choose DAILY retrieval")
            failures += 1

        manager.handle("Remember that I prefer Python.")
        python_memories = [m for m in manager.data.long_term if "python" in m.content.lower()]
        if len(python_memories) != 1:
            print("FAIL duplicate prevention created repeated Python preference")
            failures += 1

        manager.handle("Remember that I now prefer Java.")
        active_preferences = [m for m in manager.data.long_term if m.category == "PREFERENCE" and m.status == MemoryStatus.ACTIVE.value]
        if len(active_preferences) != 1 or "java" not in active_preferences[0].content.lower():
            print("FAIL contradiction handling did not leave Java as current preference")
            failures += 1

        manager.handle("Forget that I prefer Java.")
        active_after_forget = [m for m in manager.data.long_term if m.category == "PREFERENCE" and m.status == MemoryStatus.ACTIVE.value]
        if active_after_forget:
            print("FAIL forget did not remove active Java preference")
            failures += 1

        math_plan = manager.plan("What is 5 × 8?")
        if math_plan.retrieval != RetrievalDecision.NONE or math_plan.storage != StorageDecision.DO_NOT_STORE:
            print("FAIL math request used unnecessary memory")
            failures += 1

        manager.handle("Remember that my name is Sangeeth.")
        private_context = manager.retrieve_for_request("Write Python code.")
        if private_context.get("long_term"):
            print("FAIL private memory boundary retrieved long-term memory for external-provider style request")
            failures += 1

        limited = MemoryManager(path=root / "limited.json", session_context_limit=2)
        limited.observe_interaction("First session item.")
        limited.observe_interaction("Second session item.")
        limited.observe_interaction("Third session item.")
        if limited.session.recent_context != ["Second session item.", "Third session item."]:
            print("FAIL configurable session context limit was not honored")
            failures += 1

    if failures:
        return 1
    print("PASS intelligent local-first memory behavior")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
