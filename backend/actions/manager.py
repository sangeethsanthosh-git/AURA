"""Action planning, permission, confirmation, execution, and responses."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from backend.actions.executor import ActionExecutor
from backend.actions.logger import ActionLogger
from backend.actions.models import ActionRequest, PermissionDecision
from backend.actions.permissions import PermissionManager
from backend.actions.planner import ActionPlanner
from backend.utils.responses import error_response, success_response
from backend.vision.verification import ActionVerifier


class ActionManager:
    CONFIRM_WORDS = {"yes", "confirm", "proceed", "do it", "go ahead"}
    CANCEL_WORDS = {"no", "cancel", "stop", "abort", "never mind"}

    def __init__(
        self,
        planner: ActionPlanner | None = None,
        permission_manager: PermissionManager | None = None,
        executor: ActionExecutor | None = None,
        logger: ActionLogger | None = None,
        verifier: ActionVerifier | None = None,
        confirmation_ttl_seconds: int = 300,
    ) -> None:
        self.planner = planner or ActionPlanner()
        self.permission_manager = permission_manager or PermissionManager()
        self.executor = executor or ActionExecutor()
        self.logger = logger or ActionLogger()
        self.verifier = verifier or ActionVerifier()
        self.pending_action: ActionRequest | None = None
        self.pending_expires_at: datetime | None = None
        self.confirmation_ttl = timedelta(seconds=confirmation_ttl_seconds)

    def handle(self, user_input: str) -> dict[str, Any]:
        normalized = " ".join(user_input.lower().strip().split())
        if normalized in self.CONFIRM_WORDS:
            return self.confirm_pending()
        if normalized in self.CANCEL_WORDS:
            return self.cancel_pending()

        actions = self.planner.plan(user_input)
        if not actions:
            return error_response("actions", "plan", "I could not identify a supported computer action in that request.")
        if len(actions) > 1:
            return error_response("actions", "plan", "Multi-step action plans are not enabled in AURA HANDS V1.")
        action = actions[0]
        decision = self.permission_manager.check_permission(action)
        if decision == PermissionDecision.BLOCKED:
            return error_response("actions", action.action_type.value, "That action is blocked in AURA HANDS V1.")
        if decision == PermissionDecision.CONFIRM_REQUIRED:
            self.pending_action = action
            self.pending_expires_at = datetime.now(timezone.utc) + self.confirmation_ttl
            message = self._confirmation_message(action)
            response = success_response("actions", "confirmation_required", {"pending_confirmation": action.safe_dict()}, message)
            response["execution_source"] = "AURA HANDS Permission Manager"
            response["llm_used"] = False
            return response
        return self._execute(action)

    def confirm_pending(self) -> dict[str, Any]:
        if not self.pending_action or not self.pending_expires_at:
            return error_response("actions", "confirm", "There is no pending action to confirm.")
        if datetime.now(timezone.utc) > self.pending_expires_at:
            self.pending_action = None
            self.pending_expires_at = None
            return error_response("actions", "confirm", "The pending action expired. Please request it again.")
        action = self.pending_action
        self.pending_action = None
        self.pending_expires_at = None
        return self._execute(action)

    def cancel_pending(self) -> dict[str, Any]:
        if not self.pending_action:
            return success_response("actions", "cancel", {"cancelled": False}, "No pending action was active.")
        action_id = self.pending_action.action_id
        self.pending_action = None
        self.pending_expires_at = None
        response = success_response("actions", "cancel", {"cancelled": True, "action_id": action_id}, "Cancelled the pending action.")
        response["execution_source"] = "AURA HANDS Permission Manager"
        response["llm_used"] = False
        return response

    def _execute(self, action: ActionRequest) -> dict[str, Any]:
        result = self.executor.execute(action)
        self.logger.log(action, result)
        verification = self.verifier.verify(action, result)
        if result.success:
            response = success_response(
                "actions",
                action.action_type.value,
                {
                    "action_result": result.to_response_data(),
                    "verification": verification.safe_dict() if verification else None,
                },
                self._message_with_verification(result.message, verification),
            )
        else:
            response = error_response("actions", action.action_type.value, result.error or result.message, details=result.to_response_data())
        response["execution_source"] = result.execution_source
        response["llm_used"] = False
        return response

    @staticmethod
    def _confirmation_message(action: ActionRequest) -> str:
        return (
            "I am ready to perform this action:\n\n"
            f"Action: {action.action_type.value.replace('_', ' ')}\n"
            f"Target: {action.target}\n\n"
            "Please confirm with yes/proceed or cancel with no/cancel."
        )

    @staticmethod
    def _message_with_verification(message: str, verification) -> str:
        if not verification:
            return message
        if verification.success:
            return f"{message}\n\nVerified: {verification.observed}"
        return f"{message}\n\nVerification note: {verification.observed}"
