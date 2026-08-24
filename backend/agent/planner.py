"""Task planner that emits only validated Hands action requests."""

from __future__ import annotations

import logging
import re

from backend.actions.models import ActionRequest, ActionType, RiskLevel
from backend.actions.planner import ActionPlanner
from backend.agent.models import ActionStep, TaskPlan
from backend.agent.models import TaskState

LOGGER = logging.getLogger(__name__)


class TaskPlanner:
    def __init__(self, action_planner: ActionPlanner | None = None, max_steps: int = 8) -> None:
        self.action_planner = action_planner or ActionPlanner()
        self.max_steps = max_steps

    def plan(self, user_request: str) -> TaskPlan:
        parts = self._split_request(user_request)
        actions: list[ActionRequest] = []
        active_target: str | None = None
        for part in parts:
            planned = self.action_planner.plan(part)
            if not planned:
                continue
            for action in planned:
                action = self._apply_context(action, active_target)
                actions.append(action)
                if action.action_type in {ActionType.OPEN_APPLICATION, ActionType.FOCUS_APPLICATION}:
                    active_target = action.target

        if not actions:
            actions = self._compound_special_cases(user_request)

        if len(actions) > self.max_steps:
            plan = TaskPlan(user_request, [], max_steps=self.max_steps)
            plan.status = TaskState.BLOCKED
            plan.error = f"Task exceeds maximum step limit: {self.max_steps}"
            return plan

        steps = [ActionStep(action, self._verification_method(action)) for action in actions]
        plan = TaskPlan(user_request, steps, max_steps=self.max_steps)
        risks = [step.action.risk_level for step in steps]
        if RiskLevel.BLOCKED in risks:
            plan.risk_level = RiskLevel.BLOCKED
        elif RiskLevel.CONFIRMATION_REQUIRED in risks:
            plan.risk_level = RiskLevel.CONFIRMATION_REQUIRED
            plan.requires_confirmation = True
        self._log_plan(plan)
        return plan

    def _split_request(self, user_request: str) -> list[str]:
        text = user_request.strip().strip(".")
        if re.search(r"\b(search|create|rename|copy|move|open|launch|start|play|pause|stop|next|previous|close|focus|switch to|type|write)\b", text, re.IGNORECASE):
            return [
                part.strip(" ,.")
                for part in re.split(
                    r"\b(?:and then|after that|followed by|once it opens|after opening|then|next|(?<!\d\s)and(?!\s+\d))\b",
                    text,
                    flags=re.IGNORECASE,
                )
                if part.strip(" ,.")
            ]
        return [text]

    @staticmethod
    def _apply_context(action: ActionRequest, active_target: str | None) -> ActionRequest:
        media_actions = {ActionType.PLAY_MEDIA, ActionType.PAUSE_MEDIA, ActionType.STOP_MEDIA, ActionType.NEXT_MEDIA, ActionType.PREVIOUS_MEDIA}
        if action.action_type in media_actions and action.target == "active_media_app" and active_target:
            return ActionRequest(action.action_type, active_target, {**action.parameters, "inferred_from_previous_step": True}, action.risk_level, action.requires_confirmation)
        return action

    def _compound_special_cases(self, user_request: str) -> list[ActionRequest]:
        match = re.match(r"^open\s+(.+?)\s+and\s+search\s+for\s+(.+)$", user_request.strip(), re.IGNORECASE)
        if not match:
            return []
        app_actions = self.action_planner.plan(f"Open {match.group(1).strip()}")
        search_actions = self.action_planner.plan(f"Search Google for {match.group(2).strip()}")
        return [*app_actions, *search_actions]

    @staticmethod
    def _verification_method(action: ActionRequest) -> str:
        if action.action_type in {ActionType.CREATE_FOLDER, ActionType.RENAME_FILE, ActionType.COPY_FILE, ActionType.MOVE_FILE}:
            return "filesystem"
        if action.action_type in {ActionType.OPEN_APPLICATION, ActionType.OPEN_WEBSITE, ActionType.WEB_SEARCH, ActionType.FOCUS_APPLICATION}:
            return "visual_if_available"
        if action.action_type in {
            ActionType.CALCULATE,
            ActionType.TYPE_TEXT,
            ActionType.PLAY_MEDIA,
            ActionType.PAUSE_MEDIA,
            ActionType.STOP_MEDIA,
            ActionType.NEXT_MEDIA,
            ActionType.PREVIOUS_MEDIA,
            ActionType.CLOSE_APPLICATION,
        }:
            return "not_required"
        return "not_required"

    @staticmethod
    def _log_plan(plan: TaskPlan) -> None:
        lines = [
            "\n========================================",
            "AURA TASK PLAN",
            "========================================",
            f"User Request:\n{plan.user_request}",
            "\nIntent:\nComputer Actions",
            "\nSteps:",
        ]
        for index, step in enumerate(plan.steps, start=1):
            target_label = "Expression" if step.action.action_type == ActionType.CALCULATE else "Target"
            lines.append(f"{index}. {step.action.action_type.name} -> {step.action.target}")
            if target_label == "Expression":
                lines.append(f"   Expression: {step.action.target}")
        lines.append("========================================")
        LOGGER.info("\n".join(lines))
