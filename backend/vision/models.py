"""Structured models for AURA EYES V1."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any


class ScreenAnalysisTask(StrEnum):
    SCREEN_DESCRIPTION = "screen_description"
    OCR = "ocr"
    TEXT_RECOGNITION = "text_recognition"
    UI_ELEMENT_DETECTION = "ui_element_detection"
    ERROR_UNDERSTANDING = "error_understanding"
    APPLICATION_UNDERSTANDING = "application_understanding"
    APPLICATION_IDENTIFICATION = "application_identification"
    WINDOW_IDENTIFICATION = "window_identification"
    UI_ELEMENT_DISCOVERY = "ui_element_discovery"
    ACTION_VERIFICATION = "action_verification"
    TARGET_LOCATION = "target_location"
    VISUAL_REASONING = "visual_reasoning"


class CaptureRegionType(StrEnum):
    FULL_SCREEN = "full_screen"
    ACTIVE_WINDOW = "active_window"
    REGION = "region"


class VerificationState(StrEnum):
    VERIFIED = "verified"
    FAILED = "failed"
    NOT_AVAILABLE = "not_available"
    AMBIGUOUS = "ambiguous"
    TIMEOUT = "timeout"
    NOT_REQUIRED = "not_required"


@dataclass(frozen=True)
class ScreenCaptureResult:
    success: bool
    width: int = 0
    height: int = 0
    monitor: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    temporary_path: Path | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def safe_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "width": self.width,
            "height": self.height,
            "monitor": self.monitor,
            "timestamp": self.timestamp.isoformat(),
            "temporary_path": str(self.temporary_path) if self.temporary_path else None,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class VisibleElement:
    element_type: str
    label: str | None = None
    text: str | None = None
    bounding_box: tuple[int, int, int, int] | None = None
    confidence: float | None = None

    def safe_dict(self) -> dict[str, Any]:
        return {
            "element_type": self.element_type,
            "label": self.label,
            "text": self.text,
            "bounding_box": self.bounding_box,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class VisualContext:
    screen_id: str
    created_at: datetime
    expires_at: datetime
    task: ScreenAnalysisTask
    application: str | None = None
    window_title: str | None = None
    visible_text: str | None = None
    description: str | None = None
    elements: list[VisibleElement] = field(default_factory=list)
    confidence: float | None = None
    source: str = "unknown"
    sensitive: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at

    def safe_dict(self) -> dict[str, Any]:
        return {
            "screen_id": self.screen_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "task": self.task.value,
            "application": self.application,
            "window_title": self.window_title,
            "visible_text": self.visible_text,
            "description": self.description,
            "elements": [element.safe_dict() for element in self.elements],
            "confidence": self.confidence,
            "source": self.source,
            "sensitive": self.sensitive,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class VisionResult:
    success: bool
    task: ScreenAnalysisTask
    description: str
    provider: str
    model: str | None = None
    error: str | None = None
    visible_text: str | None = None
    elements: list[VisibleElement] = field(default_factory=list)
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def safe_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "task": self.task.value,
            "description": self.description,
            "provider": self.provider,
            "model": self.model,
            "error": self.error,
            "visible_text": self.visible_text,
            "elements": [element.safe_dict() for element in self.elements],
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ActionVerificationResult:
    action_id: str
    success: bool
    observed: str
    expected_state: str
    confidence: float | None
    evidence: str
    verification_method: str
    error: str | None = None
    verification_status: str = "unknown"

    def safe_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "success": self.success,
            "observed": self.observed,
            "expected_state": self.expected_state,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "verification_method": self.verification_method,
            "error": self.error,
            "verification_status": self.verification_status,
        }
