"""Rule-based memory promotion decisions."""

from __future__ import annotations

from backend.memory.memory_models import ExtractionResult, MemoryCategory, MemoryImportance
from backend.memory.memory_utils import LIST_FIELDS, PREFERENCE_FIELDS, PROFILE_FIELDS


class MemoryPromoter:
    """Maps extracted information to long-term categories and importance."""

    def classify(self, extraction: ExtractionResult, explicit: bool = False) -> tuple[str, str]:
        if extraction.field in PROFILE_FIELDS:
            return MemoryCategory.PERSONAL_FACT.value, MemoryImportance.HIGH.value if explicit else MemoryImportance.MEDIUM.value
        if extraction.field in PREFERENCE_FIELDS:
            return MemoryCategory.PREFERENCE.value, MemoryImportance.HIGH.value if explicit else MemoryImportance.MEDIUM.value
        if extraction.field == "goals":
            return MemoryCategory.GOAL.value, MemoryImportance.HIGH.value if explicit else MemoryImportance.MEDIUM.value
        if extraction.field == "projects":
            return MemoryCategory.PROJECT_CONTEXT.value, MemoryImportance.MEDIUM.value
        if extraction.field in LIST_FIELDS:
            return MemoryCategory.IMPORTANT_CONTEXT.value, MemoryImportance.MEDIUM.value
        return MemoryCategory.CUSTOM.value, MemoryImportance.MEDIUM.value

    @staticmethod
    def content_for(extraction: ExtractionResult) -> str:
        if extraction.category == "preferences" or extraction.field in PREFERENCE_FIELDS:
            return f"User prefers {extraction.value}."
        if extraction.field == "name":
            return f"User name is {extraction.value}."
        if extraction.field == "goals":
            return f"User goal: {extraction.value}."
        if extraction.field == "projects":
            return f"User project context: {extraction.value}."
        return f"User {extraction.field.replace('_', ' ')}: {extraction.value}."
