"""Local action logging without sensitive payload capture."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.actions.models import ActionRequest, ActionResult


class ActionLogger:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("backend/data/action_log.jsonl")

    def log(self, action: ActionRequest, result: ActionResult, task_id: str | None = None, step_id: str | None = None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "step_id": step_id,
            "action_type": action.action_type.value,
            "target": action.target,
            "risk_level": action.risk_level.value,
            "result": "success" if result.success else "failure",
            "success": result.success,
            "execution_time": result.execution_time,
            "error": result.error,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")
