"""TTL-bound temporary context for web, task, screen, and file work."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from backend.context.models import ContextItem, ContextSourceType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TemporaryContextRecord:
    record_id: str
    source_type: ContextSourceType
    content: str
    created_at: datetime
    expires_at: datetime
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def expired(self, now: datetime | None = None) -> bool:
        return (now or utc_now()) >= self.expires_at

    def to_item(self) -> ContextItem:
        return ContextItem(
            source_type=self.source_type,
            content=self.content,
            trust="temporary_untrusted" if self.source_type == ContextSourceType.WEB_RESEARCH else "temporary",
            label=self.label,
            metadata={**self.metadata, "record_id": self.record_id, "expires_at": self.expires_at.isoformat()},
            temporary=True,
        )


class TemporaryContextStore:
    """In-memory temporary context with explicit expiry and no durable writes."""

    def __init__(self, default_ttl_seconds: int = 1800) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._records: list[TemporaryContextRecord] = []

    def add(
        self,
        source_type: ContextSourceType,
        content: str,
        *,
        label: str = "",
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TemporaryContextRecord:
        now = utc_now()
        record = TemporaryContextRecord(
            record_id=uuid4().hex,
            source_type=source_type,
            content=content.strip(),
            label=label,
            metadata=metadata or {},
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds or self.default_ttl_seconds),
        )
        self._records.append(record)
        self.cleanup()
        return record

    def items(self, source_type: ContextSourceType | None = None) -> list[ContextItem]:
        self.cleanup()
        records = self._records
        if source_type is not None:
            records = [record for record in records if record.source_type == source_type]
        return [record.to_item() for record in records]

    def clear(self, source_type: ContextSourceType | None = None) -> int:
        before = len(self._records)
        if source_type is None:
            self._records.clear()
        else:
            self._records = [record for record in self._records if record.source_type != source_type]
        return before - len(self._records)

    def cleanup(self) -> int:
        now = utc_now()
        before = len(self._records)
        self._records = [record for record in self._records if not record.expired(now)]
        return before - len(self._records)
