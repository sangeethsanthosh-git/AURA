"""
AURA Security Audit Logger
Maintains a tamper-evident, structured audit log of all security events,
permission checks, policy enforcements, blocked threats, and emergency stops.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class SecurityAuditLogger:
    """Central audit logging service for zero-trust compliance."""

    def __init__(self, log_dir: Optional[Path] = None, max_memory_records: int = 150):
        if log_dir is None:
            log_dir = Path(__file__).resolve().parent.parent / "data"
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "security_audit.jsonl"
        self.max_memory_records = max_memory_records
        self._memory_buffer: List[Dict[str, Any]] = []

    def log_event(
        self,
        event_type: str,
        risk_level: str,
        target: str,
        decision: str,
        reason: str,
        provenance: str = "TRUSTED_USER",
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record a structured security event.
        Returns the logged event dict.
        """
        record: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "risk_level": risk_level,
            "target": target,
            "decision": decision,
            "reason": reason,
            "provenance": provenance,
            "details": details or {},
        }

        # Append to in-memory circular buffer
        self._memory_buffer.append(record)
        if len(self._memory_buffer) > self.max_memory_records:
            self._memory_buffer.pop(0)

        # Append to persistent JSONL file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.error(f"Failed to write to security audit log: {e}")

        # Also emit to python logger
        log_level = logging.WARNING if decision in ("BLOCKED", "DENIED", "INJECTION_DETECTED") else logging.INFO
        logger.log(log_level, f"[SECURITY AUDIT] {event_type} | {decision} | {target} | {reason}")

        return record

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent security audit events from memory."""
        return list(reversed(self._memory_buffer[-limit:]))

    def get_summary_stats(self) -> Dict[str, Any]:
        """Compute live audit statistics."""
        total = len(self._memory_buffer)
        blocked = sum(1 for e in self._memory_buffer if e["decision"] in ("BLOCKED", "DENIED"))
        granted = sum(1 for e in self._memory_buffer if e["decision"] == "GRANTED")
        checkpoints = sum(1 for e in self._memory_buffer if e["decision"] == "REQUIRES_CONFIRMATION")

        return {
            "total_events": total,
            "granted_count": granted,
            "blocked_count": blocked,
            "checkpoints_count": checkpoints,
            "log_path": str(self.log_file),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Alias for get_summary_stats."""
        return self.get_summary_stats()


# Global singleton instance
audit_logger = SecurityAuditLogger()
