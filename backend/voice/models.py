"""Structured voice input models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VoiceState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    STOPPING = "stopping"
    TRANSCRIBING = "transcribing"
    SUCCESS = "success"
    ERROR = "error"


@dataclass(frozen=True)
class TranscriptionResult:
    success: bool
    text: str = ""
    language: str | None = None
    confidence: float | None = None
    duration_seconds: float = 0.0
    engine: str = "unknown"
    error: str | None = None
