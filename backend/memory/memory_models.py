"""Typed models used by AURA memory."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

ProfileField = Literal["name", "age", "education", "occupation", "company", "location"]
PreferenceField = Literal["favorite_language", "preferred_ai", "operating_system"]
ListField = Literal["skills", "goals", "projects"]


class MemoryCategory(StrEnum):
    PERSONAL_FACT = "PERSONAL_FACT"
    PREFERENCE = "PREFERENCE"
    PROJECT_CONTEXT = "PROJECT_CONTEXT"
    GOAL = "GOAL"
    IMPORTANT_CONTEXT = "IMPORTANT_CONTEXT"
    CUSTOM = "CUSTOM"


class MemoryImportance(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MemoryStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class RetrievalDecision(StrEnum):
    NONE = "NONE"
    SESSION = "SESSION"
    DAILY = "DAILY"
    LONG_TERM = "LONG_TERM"
    MULTIPLE = "MULTIPLE"


class StorageDecision(StrEnum):
    DO_NOT_STORE = "DO_NOT_STORE"
    SESSION_ONLY = "SESSION_ONLY"
    DAILY = "DAILY"
    LONG_TERM = "LONG_TERM"
    ASK_USER = "ASK_USER"


def utc_now_iso() -> str:
    """Return an ISO timestamp that is stable for JSON persistence."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ProfileMemory:
    """Stable facts about the user."""

    name: str = ""
    age: str = ""
    education: str = ""
    occupation: str = ""
    company: str = ""
    location: str = ""


@dataclass(slots=True)
class PreferenceMemory:
    """User preferences that should replace older values."""

    favorite_language: str = ""
    preferred_ai: str = ""
    operating_system: str = ""


@dataclass(slots=True)
class LongTermMemory:
    """Compact long-term memory record stored locally."""

    category: str
    content: str
    importance: str = MemoryImportance.MEDIUM.value
    status: str = MemoryStatus.ACTIVE.value
    source: str = "user"
    confidence: float = 0.90
    memory_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    access_count: int = 0
    last_accessed: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LongTermMemory":
        return cls(
            memory_id=str(raw.get("memory_id") or raw.get("id") or uuid4().hex),
            category=str(raw.get("category") or MemoryCategory.CUSTOM.value),
            content=str(raw.get("content") or ""),
            importance=str(raw.get("importance") or MemoryImportance.MEDIUM.value),
            status=str(raw.get("status") or MemoryStatus.ACTIVE.value),
            source=str(raw.get("source") or "user"),
            confidence=float(raw.get("confidence") or 0.90),
            created_at=str(raw.get("created_at") or utc_now_iso()),
            updated_at=str(raw.get("updated_at") or utc_now_iso()),
            access_count=int(raw.get("access_count") or 0),
            last_accessed=str(raw.get("last_accessed") or ""),
        )


@dataclass(slots=True)
class MemoryData:
    """Persistent memory schema saved to disk."""

    profile: ProfileMemory = field(default_factory=ProfileMemory)
    preferences: PreferenceMemory = field(default_factory=PreferenceMemory)
    skills: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    conversation: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    long_term: list[LongTermMemory] = field(default_factory=list)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("updated_at", None)
        return data

    @classmethod
    def empty(cls) -> "MemoryData":
        return cls()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "MemoryData":
        profile = raw.get("profile") if isinstance(raw.get("profile"), dict) else {}
        preferences = raw.get("preferences") if isinstance(raw.get("preferences"), dict) else {}
        return cls(
            profile=ProfileMemory(**{field: str(profile.get(field, "") or "") for field in ProfileMemory.__dataclass_fields__}),
            preferences=PreferenceMemory(
                **{field: str(preferences.get(field, "") or "") for field in PreferenceMemory.__dataclass_fields__}
            ),
            skills=_clean_list(raw.get("skills")),
            goals=_clean_list(raw.get("goals")),
            conversation=_clean_list(raw.get("conversation")),
            projects=_clean_list(raw.get("projects")),
            long_term=_clean_long_term(raw.get("long_term")),
            updated_at=str(raw.get("updated_at") or utc_now_iso()),
        )


@dataclass(slots=True)
class ExtractionResult:
    """A detected memory entity from user text."""

    category: str
    field: str
    value: str
    confidence: float
    is_list: bool = False


@dataclass(slots=True)
class MemoryDecision:
    """Result of deciding whether a request should be handled by memory."""

    requires_memory: bool
    operation: str = "none"
    category: str | None = None
    field: str | None = None
    value: str | None = None
    confidence: float = 0.0


@dataclass(slots=True)
class MemoryPlan:
    """Pre-routing decision about local memory retrieval and storage."""

    retrieval: RetrievalDecision = RetrievalDecision.NONE
    storage: StorageDecision = StorageDecision.DO_NOT_STORE
    reason: str = "No memory needed."
    category: str | None = None
    query: str = ""
    confidence: float = 0.0


@dataclass(slots=True)
class SessionMemory:
    """Memory that exists only for the current process."""

    conversation: list[str] = field(default_factory=list)
    current_topic: str | None = None
    recent_context: list[str] = field(default_factory=list)
    context_limit: int = 8


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text.lower() not in {existing.lower() for existing in cleaned}:
            cleaned.append(text)
    return cleaned


def _clean_long_term(value: Any) -> list[LongTermMemory]:
    if not isinstance(value, list):
        return []
    memories: list[LongTermMemory] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        memory = LongTermMemory.from_dict(item)
        key = memory.content.strip().lower()
        if not key or key in seen:
            continue
        memories.append(memory)
        seen.add(key)
    return memories
