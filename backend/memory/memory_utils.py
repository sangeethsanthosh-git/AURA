"""Natural-language helpers for AURA memory."""

from __future__ import annotations

import re

FORGET_EVERYTHING_TERMS = {"forget everything", "clear all memory", "delete all memory"}
CLEAR_SESSION_TERMS = {"clear session memory", "reset session memory"}

PROFILE_FIELDS = {"name", "age", "education", "occupation", "company", "location"}
PREFERENCE_FIELDS = {"favorite_language", "preferred_ai", "operating_system"}
LIST_FIELDS = {"skills", "goals", "projects"}

FIELD_LABELS = {
    "name": "name",
    "age": "age",
    "education": "education",
    "occupation": "occupation",
    "company": "company",
    "location": "location",
    "favorite_language": "favorite language",
    "preferred_ai": "preferred AI",
    "operating_system": "operating system",
    "skills": "skills",
    "goals": "goals",
    "projects": "projects",
}

FORGET_ALIASES = {
    "name": ("name",),
    "age": ("age",),
    "education": ("education", "study", "studying", "degree", "course"),
    "occupation": ("occupation", "job", "profession", "work"),
    "company": ("company", "workplace"),
    "location": ("location", "where i live", "city", "place"),
    "favorite_language": ("favorite language", "favourite language", "programming language"),
    "preferred_ai": ("preferred ai", "ai preference"),
    "operating_system": ("operating system", "os"),
    "skills": ("skills", "languages i know", "technologies i know"),
    "goals": ("goals",),
    "projects": ("projects",),
}


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def clean_value(value: str) -> str:
    value = value.strip(" .!?")
    return value[:1].upper() + value[1:] if value else value


def clean_age(value: str) -> str:
    return re.sub(r"\D+", "", value)


def append_unique(items: list[str], value: str) -> bool:
    normalized = value.strip()
    if not normalized:
        return False
    if normalized.lower() in {item.lower() for item in items}:
        return False
    items.append(normalized)
    return True


def field_label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace("_", " "))


def forget_field_from_text(text: str) -> str | None:
    lowered = text.lower()
    for field, aliases in FORGET_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return field
    return None
