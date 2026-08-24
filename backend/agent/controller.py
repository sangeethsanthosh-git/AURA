"""Bounded task controller for AURA AGENT LOOP V1."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.actions.manager import ActionManager
from backend.actions.models import ActionType, PermissionDecision, RiskLevel
from backend.agent.models import ActionStep, StepStatus, TaskPlan, TaskState, VerificationStatus
from backend.agent.planner import TaskPlanner
from backend.context.models import ContextSourceType
from backend.context.temporary import TemporaryContextStore
from backend.utils.responses import error_response, success_response

LOGGER = logging.getLogger(__name__)


class TaskController:
    CONFIRM_WORDS = {"yes", "confirm", "proceed", "do it", "go ahead"}
    CANCEL_WORDS = {"no", "cancel", "stop", "abort", "never mind"}

    def __init__(
        self,
        action_manager: ActionManager | None = None,
        planner: TaskPlanner | None = None,
        max_steps: int = 8,
        max_retries_per_step: int = 1,
        max_total_retries: int = 2,
        max_visual_verifications: int = 5,
        confirmation_ttl_seconds: int = 300,
    ) -> None:
        self.action_manager = action_manager or ActionManager()
        self.planner = planner or TaskPlanner(self.action_manager.planner, max_steps=max_steps)
        self.max_steps = max_steps
        self.max_retries_per_step = max_retries_per_step
        self.max_total_retries = max_total_retries
        self.max_visual_verifications = max_visual_verifications
        self.confirmation_ttl = timedelta(seconds=confirmation_ttl_seconds)
        self.pending_task: TaskPlan | None = None
        self.pending_expires_at: datetime | None = None
        self.temporary_context: TemporaryContextStore | None = None
        self.total_retries = 0
        self.visual_verifications = 0

    def handle(self, user_input: str) -> dict[str, Any]:
        normalized = " ".join(user_input.lower().strip().split())
        if normalized in self.CANCEL_WORDS:
            return self.cancel_pending()
        if normalized in self.CONFIRM_WORDS:
            return self.confirm_pending()

        plan = self.planner.plan(user_input)
        validation_error = self._validate_plan(plan)
        if validation_error:
            plan.status = TaskState.BLOCKED
            plan.error = validation_error
            return self._blocked_response(plan, validation_error)

        first_confirmation = self._next_confirmation_step(plan)
        if first_confirmation is not None and first_confirmation == 0:
            return self._wait_for_confirmation(plan, first_confirmation)

        return self._run_until_pause_or_done(plan)

    def confirm_pending(self) -> dict[str, Any]:
        if not self.pending_task or not self.pending_expires_at:
            return error_response("agent", "confirm", "There is no pending task to confirm.")
        if datetime.now(timezone.utc) > self.pending_expires_at:
            self.pending_task.status = TaskState.FAILED
            self.pending_task.error = "Pending task confirmation expired."
            self.pending_task = None
            self.pending_expires_at = None
            return error_response("agent", "confirm", "The pending task expired. Please request it again.")
        plan = self.pending_task
        self.pending_task = None
        self.pending_expires_at = None
        return self._run_until_pause_or_done(plan)

    def cancel_pending(self) -> dict[str, Any]:
        if not self.pending_task:
            return success_response("agent", "cancel", {"cancelled": False}, "No pending task was active.")
        self.pending_task.status = TaskState.CANCELLED
        for step in self.pending_task.steps[self.pending_task.current_step :]:
            if step.status in {StepStatus.PENDING, StepStatus.WAITING_FOR_CONFIRMATION}:
                step.status = StepStatus.CANCELLED
        task = self.pending_task
        self.pending_task = None
        self.pending_expires_at = None
        return self._success("cancel", task, "Cancelled the pending task.")

    def _run_until_pause_or_done(self, plan: TaskPlan) -> dict[str, Any]:
        plan.status = TaskState.EXECUTING
        while plan.current_step < len(plan.steps):
            if plan.current_step >= self.max_steps:
                plan.status = TaskState.FAILED
                plan.error = "Maximum task step limit reached."
                return self._failure("execute", plan, plan.error)

            step = plan.steps[plan.current_step]
            decision = self.action_manager.permission_manager.check_permission(step.action)
            if decision == PermissionDecision.BLOCKED:
                step.status = StepStatus.BLOCKED
                plan.status = TaskState.BLOCKED
                plan.error = "A task step is blocked by the permission manager."
                return self._blocked_response(plan, plan.error)
            if decision == PermissionDecision.CONFIRM_REQUIRED and step.status != StepStatus.WAITING_FOR_CONFIRMATION:
                return self._wait_for_confirmation(plan, plan.current_step)

            outcome = self._execute_step(plan, step)
            if not outcome:
                return self._failure("execute", plan, plan.error or "Task failed.")
            plan.current_step += 1

        plan.status = TaskState.COMPLETED
        return self._success("complete", plan, self._summary(plan))

    def _execute_step(self, plan: TaskPlan, step: ActionStep) -> bool:
        while True:
            step.status = StepStatus.EXECUTING
            result = self.action_manager.executor.execute(step.action)
            step.result = result
            self._log_step(plan, step, result)
            self.action_manager.logger.log(step.action, result, task_id=plan.task_id, step_id=step.step_id)
            if not result.success:
                if self._can_retry(step):
                    self._mark_retry(step, plan)
                    continue
                step.status = StepStatus.FAILED
                plan.status = TaskState.FAILED
                plan.error = result.error or result.message
                return False

            step.status = StepStatus.VERIFYING
            verification = self.action_manager.verifier.verify(step.action, result)
            step.verification = verification.safe_dict() if verification else {"status": VerificationStatus.NOT_REQUIRED.value}
            if verification and verification.verification_method == "AURA EYES":
                self.visual_verifications += 1
                if self.visual_verifications > self.max_visual_verifications:
                    plan.status = TaskState.FAILED
                    plan.error = "Maximum visual verification limit reached."
                    step.status = StepStatus.FAILED
                    return False
            if verification and not verification.success and verification.verification_method not in {"Provider capability check", "vision_unavailable"}:
                if self._can_retry(step):
                    self._mark_retry(step, plan)
                    continue
                step.status = StepStatus.FAILED
                plan.status = TaskState.FAILED
                plan.error = verification.error or verification.observed
                return False
            step.status = StepStatus.COMPLETED
            return True

    def _wait_for_confirmation(self, plan: TaskPlan, step_index: int) -> dict[str, Any]:
        plan.status = TaskState.WAITING_FOR_CONFIRMATION
        plan.current_step = step_index
        plan.steps[step_index].status = StepStatus.WAITING_FOR_CONFIRMATION
        self.pending_task = plan
        self.pending_expires_at = datetime.now(timezone.utc) + self.confirmation_ttl
        self._remember_task_temporarily(plan, "pending confirmation")
        action = plan.steps[step_index].action
        message = (
            "I planned this task and need confirmation before continuing:\n\n"
            f"{self._plan_lines(plan)}\n\n"
            f"Confirmation required for step {step_index + 1}: {action.action_type.value.replace('_', ' ')} -> {action.target}\n\n"
            "Please confirm with yes/proceed or cancel with no/cancel."
        )
        return self._success("confirmation_required", plan, message, pending=True)

    def _validate_plan(self, plan: TaskPlan) -> str | None:
        if plan.error:
            return plan.error
        if not plan.steps:
            return "I could not create a supported computer task plan for that request."
        if len(plan.steps) > self.max_steps:
            return f"Task exceeds maximum step limit: {self.max_steps}"
        allowed = {
            ActionType.OPEN_APPLICATION,
            ActionType.OPEN_WEBSITE,
            ActionType.WEB_SEARCH,
            ActionType.OPEN_FILE,
            ActionType.OPEN_FOLDER,
            ActionType.CALCULATE,
            ActionType.TYPE_TEXT,
            ActionType.CLOSE_APPLICATION,
            ActionType.FOCUS_APPLICATION,
            ActionType.PLAY_MEDIA,
            ActionType.PAUSE_MEDIA,
            ActionType.STOP_MEDIA,
            ActionType.NEXT_MEDIA,
            ActionType.PREVIOUS_MEDIA,
            ActionType.PRESS_KEY,
            ActionType.CLICK,
            ActionType.SCROLL,
            ActionType.WAIT,
            ActionType.CREATE_FOLDER,
            ActionType.RENAME_FILE,
            ActionType.COPY_FILE,
            ActionType.MOVE_FILE,
            ActionType.BLOCKED,
        }
        for step in plan.steps:
            if step.action.action_type not in allowed:
                return f"Unsupported action type in task plan: {step.action.action_type}"
            if step.action.parameters.get("ambiguity") == "missing_target":
                return str(step.action.parameters.get("clarification") or "Which target would you like me to open?")
            if step.action.risk_level == RiskLevel.BLOCKED:
                return "The task contains an action blocked in AURA AGENT LOOP V1."
        return None

    def _next_confirmation_step(self, plan: TaskPlan) -> int | None:
        for index, step in enumerate(plan.steps):
            if self.action_manager.permission_manager.check_permission(step.action) == PermissionDecision.CONFIRM_REQUIRED:
                return index
        return None

    def _can_retry(self, step: ActionStep) -> bool:
        return step.retries < self.max_retries_per_step and self.total_retries < self.max_total_retries

    def _mark_retry(self, step: ActionStep, plan: TaskPlan) -> None:
        step.retries += 1
        self.total_retries += 1
        plan.status = TaskState.REPLANNING

    def _success(self, action: str, plan: TaskPlan, message: str, pending: bool = False) -> dict[str, Any]:
        if not pending:
            self._remember_task_temporarily(plan, action)
        response = success_response("agent", action, {"task": plan.safe_dict(), "pending_confirmation": pending}, message)
        response["execution_source"] = "AURA Agent Loop"
        response["llm_used"] = False
        return response

    def _failure(self, action: str, plan: TaskPlan, message: str) -> dict[str, Any]:
        response = error_response("agent", action, self._truthful_failure_message(plan, message), details={"task": plan.safe_dict()})
        response["execution_source"] = "AURA Agent Loop"
        response["llm_used"] = False
        return response

    def _blocked_response(self, plan: TaskPlan, message: str) -> dict[str, Any]:
        self._remember_task_temporarily(plan, "blocked")
        response = error_response("agent", "blocked", message, details={"task": plan.safe_dict()})
        response["execution_source"] = "AURA Agent Loop"
        response["llm_used"] = False
        return response

    def _summary(self, plan: TaskPlan) -> str:
        lines = ["Task completed."]
        for index, step in enumerate(plan.steps, start=1):
            result_text = step.result.message if step.result else step.status.value
            verification = step.verification or {}
            observed = verification.get("observed")
            lines.append(f"{index}. {result_text}" + (f" Verification: {observed}" if observed else ""))
        return "\n".join(lines)

    @staticmethod
    def _truthful_failure_message(plan: TaskPlan, message: str) -> str:
        completed = [step for step in plan.steps if step.result and step.result.success]
        failed = next((step for step in plan.steps if step.result and not step.result.success), None)
        if not completed or not failed:
            return message
        completed_text = "; ".join(step.result.message for step in completed if step.result)
        status = failed.result.to_response_data().get("status") if failed.result else "failed"
        if status == "not_implemented":
            return f"{completed_text}, but {failed.result.message if failed.result else message}"
        return f"{completed_text}, but the next step failed: {failed.result.message if failed.result else message}"

    @staticmethod
    def _plan_lines(plan: TaskPlan) -> str:
        return "\n".join(
            f"{index}. {step.action.action_type.value.replace('_', ' ')} -> {step.action.target}"
            for index, step in enumerate(plan.steps, start=1)
        )

    def _remember_task_temporarily(self, plan: TaskPlan, label: str) -> None:
        if self.temporary_context is None:
            return
        content = f"Task {plan.task_id} status={plan.status.value} label={label}\n{self._plan_lines(plan)}"
        self.temporary_context.add(
            ContextSourceType.TASK_STATE,
            content,
            label="recent task",
            ttl_seconds=1800,
            metadata={"task_id": plan.task_id, "status": plan.status.value},
        )

    @staticmethod
    def _log_step(plan: TaskPlan, step: ActionStep, result) -> None:
        metadata = result.metadata or {}
        lines = [
            "\n========================================",
            "AURA TASK STEP",
            "========================================",
            f"Task: {plan.task_id}",
            f"Step: {step.step_id}",
            f"Action: {step.action.action_type.name}",
            f"Target: {step.action.target}",
            f"Status: {result.to_response_data().get('status', 'success' if result.success else 'failed').upper()}",
            f"Execution: {result.execution_time} sec",
        ]
        if "expression" in metadata:
            lines.append(f"Expression: {metadata.get('expression')}")
        if "result" in metadata:
            lines.append(f"Result: {metadata.get('result')}")
        if result.error:
            lines.append(f"Error: {result.error}")
        lines.append("========================================")
        LOGGER.info("\n".join(lines))
