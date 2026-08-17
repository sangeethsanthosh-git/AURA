"""Local long-term memory operations."""

from __future__ import annotations

import logging
import re

from backend.memory.memory_models import LongTermMemory, MemoryImportance, MemoryStatus, utc_now_iso

LOGGER = logging.getLogger(__name__)


class LongTermMemoryStore:
    """Manages active long-term memory records inside MemoryData."""

    def __init__(self, records: list[LongTermMemory]) -> None:
        self.records = records

    def active(self) -> list[LongTermMemory]:
        return [record for record in self.records if record.status == MemoryStatus.ACTIVE.value]

    def upsert(self, category: str, content: str, importance: str = MemoryImportance.MEDIUM.value, confidence: float = 0.90) -> LongTermMemory:
        normalized = self._normalize(content)
        for record in self.active():
            same = self._normalize(record.content) == normalized
            contradiction = category == "PREFERENCE" and record.category == "PREFERENCE"
            if same:
                record.updated_at = utc_now_iso()
                record.access_count += 1
                LOGGER.info("Long-Term Memory: duplicate prevented.")
                return record
            if contradiction:
                record.status = MemoryStatus.SUPERSEDED.value
                record.updated_at = utc_now_iso()
                LOGGER.info("Long-Term Memory: older preference superseded.")

        record = LongTermMemory(category=category, content=content, importance=importance, confidence=confidence)
        self.records.append(record)
        LOGGER.info("Long-Term Memory: created category=%s importance=%s", category, importance)
        return record

    def forget(self, query: str) -> LongTermMemory | None:
        target = self._normalize(query)
        best: LongTermMemory | None = None
        for record in self.active():
            content = self._normalize(record.content)
            if target in content or content in target or self._overlap(target, content) >= 1:
                best = record
                break
        if best:
            best.status = MemoryStatus.DELETED.value
            best.updated_at = utc_now_iso()
            LOGGER.info("Long-Term Memory: forgotten id=%s", best.memory_id)
        return best

    def retrieve(self, query: str, limit: int = 5) -> list[LongTermMemory]:
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        scored: list[tuple[int, LongTermMemory]] = []
        for record in self.active():
            content_terms = set(re.findall(r"[a-z0-9]+", record.content.lower()))
            score = len(terms & content_terms)
            if score or any(word in query.lower() for word in ("remember", "about me", "my ")):
                scored.append((score, record))
        results = [record for _, record in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]
        now = utc_now_iso()
        for record in results:
            record.access_count += 1
            record.last_accessed = now
        return results

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", text.lower()))

    @staticmethod
    def _preference_key(text: str) -> str:
        lowered = text.lower()
        if "prefer" in lowered:
            return re.sub(r"\b(now|currently|really|prefer|prefers|i|user|that)\b", " ", lowered).strip()
        return ""

    @staticmethod
    def _overlap(left: str, right: str) -> int:
        common = set(left.split()) & set(right.split())
        return len({word for word in common if len(word) > 3})
