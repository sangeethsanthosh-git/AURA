"""Voice Studio models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class VoiceEngine(StrEnum):
    PIPER = "piper"
    INDIC_F5 = "indic_f5"
    INDIC_PARLER = "indic_parler_tts"


class VoiceLanguage(StrEnum):
    ENGLISH = "en"
    MALAYALAM = "ml"
    MIXED = "mixed"


class SpeechStyle(StrEnum):
    NATURAL = "natural"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    CALM = "calm"
    ENERGETIC = "energetic"


@dataclass(frozen=True)
class VoiceProfile:
    id: str
    display_name: str
    engine: VoiceEngine
    language: VoiceLanguage
    supported_languages: tuple[str, ...]
    model_reference: str | Path
    availability: bool
    description: str
    speaker: str | None = None
    gender: str | None = None
    supported_styles: tuple[SpeechStyle, ...] = field(default_factory=lambda: (SpeechStyle.NATURAL,))
    default_speed: float = 1.0
    unavailable_reason: str | None = None
