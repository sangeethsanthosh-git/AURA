"""Shared intent types for AURA routing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Intent(StrEnum):
    """Supported high-level user intents."""

    CONVERSATION = "Conversation"
    MEMORY = "Memory"
    PROGRAMMING = "Programming"
    MATHEMATICS = "Mathematics"
    REASONING = "Reasoning"
    GENERAL_KNOWLEDGE = "General Knowledge"
    WEB_INTELLIGENCE = "Web Intelligence"
    WEATHER = "Weather"
    MAPS = "Maps"
    LOCATION = "Maps"
    TRANSLATION = "Translation"
    FINANCE = "Finance"
    FILE_OPERATIONS = "File Operations"
    COMPUTER_ACTIONS = "Computer Actions"
    VISION = "Vision"
    SYSTEM_COMMANDS = "System Commands"
    RAG = "RAG"
    DOCUMENTS = "RAG"
    UNKNOWN = "Unknown"


@dataclass(frozen=True)
class IntentResult:
    """Classifier output consumed by SmartRouter and tests."""

    intent: Intent
    confidence: float
    query: str
    provider: str
    reason: str
    needs_explanation: bool = False

    def to_dict(self) -> dict[str, str | float | bool]:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "provider": self.provider,
            "reason": self.reason,
            "query": self.query,
            "needs_explanation": self.needs_explanation,
        }
