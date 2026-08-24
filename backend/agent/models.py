"""Structured task models for bounded Eyes + Hands coordination."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from backend.actions.models import ActionRequest, ActionResult, RiskLevel


class TaskState(StrEnum):
    PLANNING = "planning"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class StepStatus(StrEnum):
    PENDING = "pending"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    FAILED = "failed"
    UNKNOWN = "unknown"
    NOT_REQUIRED = "not_required"


@dataclass
class ActionStep:
    action: ActionRequest
    verification_method: str = "auto"
    step_id: str = field(default_factory=lambda: uuid4().hex)
    status: StepStatus = StepStatus.PENDING
    result: ActionResult | None = None
    verification: dict[str, Any] | None = None
    retries: int = 0

    def safe_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action": self.action.safe_dict(),
            "verification_method": self.verification_method,
            "status": self.status.value,
            "result": self.result.to_response_data() if self.result else None,
            "verification": self.verification,
            "retries": self.retries,
        }


@dataclass
class TaskPlan:
    user_request: str
    steps: list[ActionStep]
    task_id: str = field(default_factory=lambda: uuid4().hex)
    risk_level: RiskLevel = RiskLevel.SAFE
    requires_confirmation: bool = False
    max_steps: int = 8
    current_step: int = 0
    status: TaskState = TaskState.PLANNING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None

    def safe_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "user_request": self.user_request,
            "steps": [step.safe_dict() for step in self.steps],
            "risk_level": self.risk_level.value,
            "requires_confirmation": self.requires_confirmation,
            "max_steps": self.max_steps,
            "current_step": self.current_step,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "error": self.error,
        }
