"""
AURA Central Zero-Trust Permission Gateway
Enforces multi-level granular permissions, checkpoint approvals for sensitive tasks,
least privilege, provenance tracking, and deterministic security gates.
"""

from typing import Dict, Any, List, Optional, Tuple, Callable
from enum import Enum
import uuid
import time
import logging
from backend.security.audit_logger import audit_logger

logger = logging.getLogger(__name__)


class PermissionLevel(str, Enum):
    LEVEL_1_LOW = "LEVEL_1_LOW"                # Read-only, open approved apps, volume, media, diagnostics
    LEVEL_2_CONTROLLED = "LEVEL_2_CONTROLLED"    # Move/rename files, modify docs, download files, close apps
    LEVEL_3_SENSITIVE = "LEVEL_3_SENSITIVE"      # Delete files, run scripts, upload docs, startup changes
    LEVEL_4_CRITICAL = "LEVEL_4_CRITICAL"        # Admin privileges, registry, firewall, disk format (PROHIBITED)


class PermissionDecision(str, Enum):
    GRANTED = "GRANTED"
    REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"
    DENIED = "DENIED"


class ContentProvenance(str, Enum):
    TRUSTED_USER = "TRUSTED_USER"                # Spoken by user or typed directly in input
    UNTRUSTED_EXTERNAL = "UNTRUSTED_EXTERNAL"    # Webpage, Wikipedia, email, PDF, document, OCR text


class PendingApproval:
    """Represents a sensitive operation awaiting explicit user confirmation."""

    def __init__(
        self,
        action_name: str,
        risk_level: PermissionLevel,
        target: str,
        preview_details: Dict[str, Any],
        callback: Optional[Callable[[], Dict[str, Any]]] = None,
        timeout_seconds: float = 120.0,
    ):
        self.id = f"apr-{uuid.uuid4().hex[:8]}"
        self.action_name = action_name
        self.risk_level = risk_level
        self.target = target
        self.preview_details = preview_details
        self.callback = callback
        self.created_at = time.time()
        self.timeout_seconds = timeout_seconds
        self.status = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED

    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.timeout_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_name": self.action_name,
            "risk_level": self.risk_level.value,
            "target": self.target,
            "preview_details": self.preview_details,
            "created_at": self.created_at,
            "expires_in": max(0, int(self.timeout_seconds - (time.time() - self.created_at))),
            "status": self.status,
        }


class PermissionGateway:
    """Central deterministic policy evaluation engine for AURA."""

    # Explicit Level 4 Critical commands strictly prohibited from autonomous execution
    PROHIBITED_CRITICAL_ACTIONS = {
        "format_disk",
        "diskpart",
        "registry_write",
        "firewall_disable",
        "modify_firewall",
        "firewall_modify",
        "clear_event_logs",
        "grant_admin",
        "disable_uac",
        "delete_system32",
        "modify_sam",
        "disable_antivirus",
        "kill_antivirus",
    }

    def __init__(self):
        self._pending_approvals: Dict[str, PendingApproval] = {}
        # Pre-approved capabilities (user configurable)
        self._auto_approved_level1: bool = True
        self._auto_approved_level2: bool = False

    def evaluate_request(
        self,
        action_name: str,
        target: str,
        provenance: ContentProvenance = ContentProvenance.TRUSTED_USER,
        custom_risk: Optional[PermissionLevel] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Tuple[PermissionDecision, str, PermissionLevel]:
        """
        Evaluate an action request against deterministic zero-trust policy.
        Returns (decision, reason, determined_risk_level).
        """
        # 1. Prohibit Level 4 Critical Actions
        if action_name.lower() in self.PROHIBITED_CRITICAL_ACTIONS or (details and details.get("is_admin")):
            reason = f"Action '{action_name}' requires administrative/critical privileges and is prohibited by policy"
            audit_logger.log_event(
                event_type="PERMISSION_CHECK",
                risk_level=PermissionLevel.LEVEL_4_CRITICAL.value,
                target=target,
                decision=PermissionDecision.DENIED.value,
                reason=reason,
                provenance=provenance.value,
                details=details,
            )
            return PermissionDecision.DENIED, reason, PermissionLevel.LEVEL_4_CRITICAL

        # 2. Determine Risk Tier
        risk = custom_risk or self._infer_risk_level(action_name, target, details)
        if details:
            args = details.get("arguments") or details
            if isinstance(args, dict) and (args.get("preview") is True or args.get("dry_run") is True):
                risk = PermissionLevel.LEVEL_1_LOW

        # 3. Untrusted External Content Boundary:
        # Untrusted external text (webpages, documents, OCR) can NEVER execute Level 2 or Level 3 autonomously
        if provenance == ContentProvenance.UNTRUSTED_EXTERNAL and risk in (
            PermissionLevel.LEVEL_2_CONTROLLED,
            PermissionLevel.LEVEL_3_SENSITIVE,
        ):
            reason = f"Action proposed by untrusted external content. Explicit user authorization required."
            audit_logger.log_event(
                event_type="UNTRUSTED_CONTENT_ESCALATION",
                risk_level=risk.value,
                target=target,
                decision=PermissionDecision.REQUIRES_CONFIRMATION.value,
                reason=reason,
                provenance=provenance.value,
                details=details,
            )
            return PermissionDecision.REQUIRES_CONFIRMATION, reason, risk

        # 4. Level 3 Sensitive: Always requires explicit confirmation checkpoint
        if risk == PermissionLevel.LEVEL_3_SENSITIVE:
            reason = f"Sensitive operation '{action_name}' targeting '{target}' requires explicit confirmation"
            audit_logger.log_event(
                event_type="CHECKPOINT_REQUIRED",
                risk_level=risk.value,
                target=target,
                decision=PermissionDecision.REQUIRES_CONFIRMATION.value,
                reason=reason,
                provenance=provenance.value,
                details=details,
            )
            return PermissionDecision.REQUIRES_CONFIRMATION, reason, risk

        # 5. Level 2 Controlled: Requires confirmation if not auto-approved
        if risk == PermissionLevel.LEVEL_2_CONTROLLED:
            if not self._auto_approved_level2:
                reason = f"Controlled operation '{action_name}' requires user confirmation"
                audit_logger.log_event(
                    event_type="CHECKPOINT_REQUIRED",
                    risk_level=risk.value,
                    target=target,
                    decision=PermissionDecision.REQUIRES_CONFIRMATION.value,
                    reason=reason,
                    provenance=provenance.value,
                    details=details,
                )
                return PermissionDecision.REQUIRES_CONFIRMATION, reason, risk

        # 6. Level 1 Low: Granted
        reason = f"Low-risk operation '{action_name}' approved by policy"
        audit_logger.log_event(
            event_type="PERMISSION_CHECK",
            risk_level=risk.value,
            target=target,
            decision=PermissionDecision.GRANTED.value,
            reason=reason,
            provenance=provenance.value,
            details=details,
        )
        return PermissionDecision.GRANTED, reason, risk

    def create_pending_approval(
        self,
        action_name: str,
        risk_level: PermissionLevel,
        target: str,
        preview_details: Dict[str, Any],
        callback: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> PendingApproval:
        """Register a pending checkpoint approval."""
        self._cleanup_expired()
        approval = PendingApproval(
            action_name=action_name,
            risk_level=risk_level,
            target=target,
            preview_details=preview_details,
            callback=callback,
        )
        self._pending_approvals[approval.id] = approval
        return approval

    def approve_action(self, approval_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Execute a previously approved pending checkpoint."""
        self._cleanup_expired()
        approval = self._pending_approvals.get(approval_id)
        if not approval:
            return False, "Approval request not found or expired", None

        if approval.is_expired():
            approval.status = "EXPIRED"
            del self._pending_approvals[approval_id]
            audit_logger.log_event(
                event_type="APPROVAL_EXPIRED",
                risk_level=approval.risk_level.value,
                target=approval.target,
                decision="EXPIRED",
                reason=f"Approval #{approval_id} expired before user confirmation",
            )
            return False, "Approval has expired", None

        approval.status = "APPROVED"
        audit_logger.log_event(
            event_type="PERMISSION_APPROVED",
            risk_level=approval.risk_level.value,
            target=approval.target,
            decision="APPROVED",
            reason=f"User approved checkpoint #{approval_id} for '{approval.action_name}'",
            details=approval.preview_details,
        )

        result = None
        if approval.callback:
            try:
                result = approval.callback()
            except Exception as e:
                logger.error(f"Error running approved action callback: {e}")
                return False, f"Action execution failed: {e}", None

        del self._pending_approvals[approval_id]
        return True, "Action approved and executed", result

    def reject_action(self, approval_id: str, reason: str = "User explicitly rejected action") -> Tuple[bool, str]:
        """User rejects a pending checkpoint."""
        approval = self._pending_approvals.get(approval_id)
        if not approval:
            return False, "Approval request not found"

        approval.status = "REJECTED"
        audit_logger.log_event(
            event_type="PERMISSION_REJECTED",
            risk_level=approval.risk_level.value,
            target=approval.target,
            decision="REJECTED",
            reason=f"{reason} (checkpoint #{approval_id} for '{approval.action_name}')",
        )
        del self._pending_approvals[approval_id]
        return True, "Action was cancelled by user"

    def approve(self, approval_id: str):
        """Alias for approve_action."""
        return self.approve_action(approval_id)

    def reject(self, approval_id: str, reason: str = "User explicitly rejected action"):
        """Alias for reject_action."""
        return self.reject_action(approval_id, reason=reason)

    def list_pending_approvals(self) -> List[Dict[str, Any]]:
        """List active pending approvals."""
        self._cleanup_expired()
        return [a.to_dict() for a in self._pending_approvals.values() if not a.is_expired()]

    def clear_all_pending(self) -> int:
        """Clear all pending approvals (used during Emergency Stop)."""
        count = len(self._pending_approvals)
        self._pending_approvals.clear()
        return count

    def _cleanup_expired(self) -> None:
        """Purge expired approvals."""
        expired = [aid for aid, a in self._pending_approvals.items() if a.is_expired()]
        for aid in expired:
            del self._pending_approvals[aid]

    @staticmethod
    def _infer_risk_level(action_name: str, target: str, details: Optional[Dict[str, Any]]) -> PermissionLevel:
        """Determine risk level from tool name and target parameters."""
        act = action_name.lower()

        # Level 3 Sensitive
        if any(w in act for w in ("delete", "remove", "drop", "purge", "upload_private", "run_script")):
            return PermissionLevel.LEVEL_3_SENSITIVE

        # Level 2 Controlled
        if any(w in act for w in ("organize", "move", "rename", "download", "write_file", "close_app")):
            if details and (details.get("preview") is True or details.get("dry_run") is True):
                return PermissionLevel.LEVEL_1_LOW
            return PermissionLevel.LEVEL_2_CONTROLLED

        # Default to Level 1 Low
        return PermissionLevel.LEVEL_1_LOW


# Global singleton instance
permission_gateway = PermissionGateway()
