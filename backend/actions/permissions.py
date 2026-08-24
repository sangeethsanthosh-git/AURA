"""Central permission and risk checks for AURA HANDS."""

from __future__ import annotations

from backend.actions.models import ActionRequest, PermissionDecision, RiskLevel


class PermissionManager:
    def check_permission(self, action: ActionRequest) -> PermissionDecision:
        if action.risk_level == RiskLevel.BLOCKED or action.action_type.value == "blocked":
            return PermissionDecision.BLOCKED
        if action.requires_confirmation or action.risk_level == RiskLevel.CONFIRMATION_REQUIRED:
            return PermissionDecision.CONFIRM_REQUIRED
        return PermissionDecision.ALLOWED
