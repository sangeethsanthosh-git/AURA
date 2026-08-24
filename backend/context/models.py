"""Typed context objects for AURA's unified context layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ContextSourceType(str, Enum):
    CURRENT_CONVERSATION = "current_conversation"
    SESSION = "session"
    DAILY_MEMORY = "daily_memory"
    LONG_TERM_MEMORY = "long_term_memory"
    PERSONAL_KNOWLEDGE = "personal_knowledge"
    TASK_STATE = "task_state"
    WEB_RESEARCH = "web_research"
    SYSTEM = "system"


@dataclass
class ContextItem:
    source_type: ContextSourceType
    content: str
    relevance: float = 0.0
    trust: str = "local"
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    temporary: bool = False

    def normalized_content(self) -> str:
        return " ".join(self.content.lower().split())


@dataclass
class ContextDebugEntry:
    source_type: ContextSourceType
    label: str
    decision: str
    reason: str
    relevance: float = 0.0
    size_chars: int = 0


@dataclass
class ContextBundle:
    text: str
    items: list[ContextItem]
    debug: list[ContextDebugEntry]
    budget_chars: int

    @property
    def size_chars(self) -> int:
        return len(self.text)

    def to_debug_dict(self) -> dict[str, Any]:
        return {
            "budget_chars": self.budget_chars,
            "size_chars": self.size_chars,
            "items": [
                {
                    "source_type": item.source_type.value,
                    "label": item.label,
                    "temporary": item.temporary,
                    "relevance": round(item.relevance, 3),
                    "size_chars": len(item.content),
                }
                for item in self.items
            ],
            "decisions": [
                {
                    "source_type": entry.source_type.value,
                    "label": entry.label,
                    "decision": entry.decision,
                    "reason": entry.reason,
                    "relevance": round(entry.relevance, 3),
                    "size_chars": entry.size_chars,
                }
                for entry in self.debug
            ],
        }
