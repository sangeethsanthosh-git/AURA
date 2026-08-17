"""Selective local memory retrieval."""

from __future__ import annotations

import logging
import time
from dataclasses import asdict

from backend.memory.daily_memory import DailyMemory
from backend.memory.long_term_memory import LongTermMemoryStore
from backend.memory.memory_models import MemoryPlan, RetrievalDecision, SessionMemory

LOGGER = logging.getLogger(__name__)


class MemoryRetriever:
    """Retrieves only the local memory scopes requested by a MemoryPlan."""

    def __init__(self, daily: DailyMemory) -> None:
        self.daily = daily

    def retrieve(self, plan: MemoryPlan, session: SessionMemory, long_term: LongTermMemoryStore) -> dict[str, object]:
        started = time.perf_counter()
        result: dict[str, object] = {"retrieval": plan.retrieval.value}
        if plan.retrieval in {RetrievalDecision.SESSION, RetrievalDecision.MULTIPLE}:
            result["session"] = session.recent_context[-session.context_limit :]
        if plan.retrieval in {RetrievalDecision.DAILY, RetrievalDecision.MULTIPLE}:
            result["daily"] = self.daily.read()
        if plan.retrieval in {RetrievalDecision.LONG_TERM, RetrievalDecision.MULTIPLE}:
            result["long_term"] = [asdict(memory) for memory in long_term.retrieve(plan.query)]
        LOGGER.info("Memory Retrieval Decision: %s in %.3f sec", plan.retrieval.value, time.perf_counter() - started)
        return result
