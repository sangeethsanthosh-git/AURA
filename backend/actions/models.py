"""Structured models for controlled computer actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class ActionType(StrEnum):
    OPEN_APPLICATION = "open_application"
    OPEN_WEBSITE = "open_website"
    WEB_SEARCH = "web_search"
    CALCULATE = "calculate"
    TYPE_TEXT = "type_text"
    CLOSE_APPLICATION = "close_application"
    FOCUS_APPLICATION = "focus_application"
    PLAY_MEDIA = "play_media"
    PAUSE_MEDIA = "pause_media"
    STOP_MEDIA = "stop_media"
    NEXT_MEDIA = "next_media"
    PREVIOUS_MEDIA = "previous_media"
    PRESS_KEY = "press_key"
    CLICK = "click"
    SCROLL = "scroll"
    WAIT = "wait"
    OPEN_FILE = "open_file"
    OPEN_FOLDER = "open_folder"
    CREATE_FOLDER = "create_folder"
    RENAME_FILE = "rename_file"
    COPY_FILE = "copy_file"
    MOVE_FILE = "move_file"
    BLOCKED = "blocked"


class RiskLevel(StrEnum):
    SAFE = "safe"
    CONFIRMATION_REQUIRED = "confirmation_required"
    BLOCKED = "blocked"


class PermissionDecision(StrEnum):
    ALLOWED = "allowed"
    CONFIRM_REQUIRED = "confirm_required"
    BLOCKED = "blocked"


class ActionExecutionStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    NOT_IMPLEMENTED = "not_implemented"
    BLOCKED = "blocked"
    AMBIGUOUS = "ambiguous"
    TIMEOUT = "timeout"


class TargetType(StrEnum):
    APPLICATION = "application"
    WEBSITE = "website"
    URL = "url"
    FILE = "file"
    FOLDER = "folder"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ResolvedTarget:
    target_type: TargetType
    target: str
    confidence: float
    display_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class ActionRequest:
    action_type: ActionType
    target: str
    parameters: dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.SAFE
    requires_confirmation: bool = False
    action_id: str = field(default_factory=lambda: uuid4().hex)
    status: str = "planned"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def safe_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "target": self.target,
            "parameters": self.parameters,
            "risk_level": self.risk_level.value,
            "requires_confirmation": self.requires_confirmation,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class ActionResult:
    success: bool
    action_id: str
    action_type: ActionType
    message: str
    execution_source: str
    target: str
    execution_time: float
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = ""

    def to_response_data(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "message": self.message,
            "execution_source": self.execution_source,
            "target": self.target,
            "execution_time": self.execution_time,
            "error": self.error,
            "metadata": self.metadata,
            "status": self.status or (ActionExecutionStatus.SUCCESS.value if self.success else ActionExecutionStatus.FAILED.value),
        }
