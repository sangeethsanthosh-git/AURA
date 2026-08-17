"""Natural response formatting for AURA memory."""

from __future__ import annotations

from backend.memory.memory_models import MemoryData
from backend.memory.memory_utils import field_label


class MemoryFormatter:
    """Formats memory responses without exposing storage-shaped text."""

    def remembered(self, field: str, value: str, is_list: bool = False) -> str:
        if field == "name":
            return f"Nice to meet you, {value}. I'll remember your name."
        if field == "education":
            return f"Got it! I'll remember that you're studying {value}."
        if field == "occupation":
            return f"Got it! I'll remember that you're a {value}."
        if field == "company":
            return f"Got it! I'll remember that you work at {value}."
        if field == "location":
            return f"Got it! I'll remember that you're from {value}."
        if field == "age":
            return f"Got it! I'll remember that you're {value}."
        if field == "skills":
            return f"Got it! I'll remember that you know {value}."
        if field == "goals":
            return f"Got it! I'll remember that you want to {value}."
        if field == "favorite_language":
            return f"Got it! I'll remember that your favorite language is {value}."
        return f"I've updated what I know about your {field_label(field)}."

    def recalled(self, field: str, value: str | list[str] | None) -> str:
        if not value:
            return f"I don't know your {field_label(field)} yet."
        if isinstance(value, list):
            joined = self.join_list(value)
            if field == "skills":
                return f"You know {joined}."
            if field == "goals":
                return f"Your goals include {joined}."
            return f"Your {field_label(field)} include {joined}."
        if field == "name":
            return f"Your name is {value}."
        if field == "education":
            return f"You're studying {value}."
        if field == "occupation":
            return f"You're a {value}."
        if field == "company":
            return f"You work at {value}."
        if field == "location":
            return f"You live in {value}."
        if field == "age":
            return f"You're {value}."
        return f"Your {field_label(field)} is {value}."

    def profile_summary(self, data: MemoryData) -> str:
        lines: list[str] = []
        profile = data.profile
        if profile.name:
            lines.append(f"Your name is {profile.name}.")
        if profile.age:
            lines.append(f"You're {profile.age}.")
        if profile.education:
            lines.append(f"You're studying {profile.education}.")
        if profile.occupation:
            lines.append(f"You're a {profile.occupation}.")
        if profile.company:
            lines.append(f"You work at {profile.company}.")
        if profile.location:
            lines.append(f"You live in {profile.location}.")
        if data.skills:
            lines.append(f"You know {self.join_list(data.skills)}.")
        if data.goals:
            lines.append(f"Your goals include {self.join_list(data.goals)}.")
        if data.projects:
            lines.append(f"Your projects include {self.join_list(data.projects)}.")
        prefs = data.preferences
        if prefs.favorite_language:
            lines.append(f"Your favorite language is {prefs.favorite_language}.")
        if prefs.preferred_ai:
            lines.append(f"You prefer {prefs.preferred_ai}.")
        if prefs.operating_system:
            lines.append(f"You prefer {prefs.operating_system}.")
        if not lines:
            return "I don't know much about you yet."
        return " ".join(lines)

    @staticmethod
    def join_list(items: list[str]) -> str:
        if len(items) <= 1:
            return items[0] if items else ""
        if len(items) == 2:
            return f"{items[0]} and {items[1]}"
        return ", ".join(items[:-1]) + f", and {items[-1]}"
