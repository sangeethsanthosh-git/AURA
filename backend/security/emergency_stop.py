"""
AURA Global Emergency Stop (Kill Switch) Subsystem
Instantly terminates active workflows, halts AURA-managed child processes, revokes pending
approvals, halts audio synthesis, and transitions the system into a safe state.
"""

from typing import Dict, Any, Optional, List
import logging
from backend.security.audit_logger import audit_logger
from backend.security.permission_gateway import permission_gateway
from backend.security.process_sandbox import process_sandbox

logger = logging.getLogger(__name__)


class EmergencyStopController:
    """Zero-trust emergency stop kill switch."""

    _emergency_stop_active: bool = False
    _cancel_pipeline_cb: Optional[Any] = None
    _canceller_callbacks: List[Any] = []

    @classmethod
    def register_pipeline_canceller(cls, callback) -> None:
        """Register a canceller callback (pipeline or hardware abort)."""
        cls._cancel_pipeline_cb = callback
        if callback not in cls._canceller_callbacks:
            cls._canceller_callbacks.append(callback)

    @classmethod
    def register_canceller(cls, callback) -> None:
        """Register an arbitrary emergency halt callback."""
        if callback not in cls._canceller_callbacks:
            cls._canceller_callbacks.append(callback)

    @classmethod
    def trigger(cls, reason: str = "User Initiated Emergency Stop") -> Dict[str, Any]:
        """
        Executes immediate system-wide emergency halt:
        1. Halts AURA-managed child processes.
        2. Revokes all pending permission approvals.
        3. Halts audio playback and background inference pipelines.
        4. Logs audit event.
        """
        logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
        cls._emergency_stop_active = True

        # 1. Terminate Job Object child processes
        killed_procs = process_sandbox.terminate_all_managed_processes()

        # 2. Revoke pending permission checkpoints
        revoked_approvals = permission_gateway.clear_all_pending()

        # 3. Cancel active pipelines, halt audio, release held mouse/keys
        for cb in list(cls._canceller_callbacks):
            try:
                cb()
            except Exception as e:
                logger.error(f"Error invoking emergency canceller {cb}: {e}")

        # 4. Audit Log
        audit_logger.log_event(
            event_type="EMERGENCY_STOP",
            risk_level="CRITICAL",
            target="ALL_ACTIVE_WORKFLOWS",
            decision="HALTED",
            reason=reason,
            details={
                "terminated_child_processes": killed_procs,
                "revoked_approvals": revoked_approvals,
            },
        )

        return {
            "success": True,
            "status": "HALTED",
            "reason": reason,
            "terminated_child_processes": killed_procs,
            "revoked_approvals": revoked_approvals,
        }

    @classmethod
    def reset(cls) -> Dict[str, Any]:
        """Resets the emergency stop state back to normal operational readiness."""
        cls._emergency_stop_active = False
        audit_logger.log_event(
            event_type="EMERGENCY_STOP_RESET",
            risk_level="MEDIUM",
            target="SYSTEM",
            decision="RESET",
            reason="User reset emergency stop state",
        )
        return {"success": True, "status": "OPERATIONAL"}

    @classmethod
    def is_active(cls) -> bool:
        return cls._emergency_stop_active

    @classmethod
    def is_stopped(cls) -> bool:
        return cls._emergency_stop_active


# Global singleton instance
emergency_stop = EmergencyStopController
