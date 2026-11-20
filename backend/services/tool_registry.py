"""
AURA Modular Tool Registry
Defines and registers all desktop automation, system control, file, and web tools
with schema validation, risk tiers, and execution verification.
"""

from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import logging
from backend.security.permission_gateway import (
    permission_gateway,
    PermissionLevel,
    PermissionDecision,
    ContentProvenance,
)
from backend.security.audit_logger import audit_logger

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "LEVEL_1_LOW"          # Read-only operations, app launches, media controls, volume
    MEDIUM = "LEVEL_2_CONTROLLED" # Closing apps, creating/moving files, clipboard modifications
    HIGH = "LEVEL_3_SENSITIVE"   # Destructive file deletions, system sleep/reboot/shutdown, process kills


@dataclass
class ToolDefinition:
    name: str
    description: str
    category: str
    risk_level: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    parameters_schema: Dict[str, Any] = field(default_factory=dict)
    execute: Optional[Callable[..., Dict[str, Any]]] = None
    verify: Optional[Callable[..., bool]] = None


class ToolRegistry:
    """Central registry of all executable tools available to AURA's Action Planner."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a new tool definition."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool '{tool.name}' (Category: {tool.category}, Risk: {tool.risk_level.value})")

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools with metadata."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "risk_level": t.risk_level.value,
                "requires_confirmation": t.requires_confirmation,
                "parameters": t.parameters_schema,
            }
            for t in self._tools.values()
        ]

    def execute(
        self,
        name: str,
        provenance: ContentProvenance = ContentProvenance.TRUSTED_USER,
        skip_confirmation: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute a tool with deterministic zero-trust validation,
        permission checkpoint evaluation, and post-execution state verification.
        """
        tool = self.get(name)
        if not tool:
            return {
                "handled": False,
                "success": False,
                "error": f"Tool '{name}' is not registered.",
            }

        if not tool.execute:
            return {
                "handled": False,
                "success": False,
                "error": f"Tool '{name}' does not have an execution handler.",
            }

        # Zero-Trust Security Gate: Evaluate through PermissionGateway
        target_str = str(kwargs)
        perm_level = PermissionLevel(tool.risk_level.value)
        decision, reason, determined_risk = permission_gateway.evaluate_request(
            action_name=name,
            target=target_str,
            provenance=provenance,
            custom_risk=perm_level,
            details={"arguments": kwargs, "category": tool.category},
        )

        if decision == PermissionDecision.DENIED:
            logger.warning(f"Permission Gateway DENIED tool '{name}': {reason}")
            return {
                "handled": True,
                "action": "sandbox_blocked",
                "type": "security_violation",
                "title": "AURA Security Alert",
                "message": f"Execution blocked: {reason}",
                "spoken_response": "That action was blocked by my security sandbox for your safety.",
                "data": {
                    "tool": name,
                    "reason": reason,
                    "risk_level": determined_risk.value,
                    "status": "BLOCKED",
                },
            }

        if decision == PermissionDecision.REQUIRES_CONFIRMATION and not skip_confirmation:
            logger.info(f"Permission Gateway requires user confirmation for '{name}': {reason}")
            pending = permission_gateway.create_pending_approval(
                action_name=name,
                risk_level=determined_risk,
                target=target_str,
                preview_details={"tool": name, "arguments": kwargs, "reason": reason},
                callback=lambda: tool.execute(**kwargs),
            )
            return {
                "handled": True,
                "action": "permission_checkpoint",
                "type": "checkpoint_required",
                "title": f"Confirm: {name.replace('_', ' ').title()}",
                "message": reason,
                "spoken_response": "This action requires your confirmation. Please review the approval card on your screen.",
                "data": {
                    "approval_id": pending.id,
                    "tool": name,
                    "risk_level": determined_risk.value,
                    "arguments": kwargs,
                    "preview": pending.preview_details,
                    "status": "PENDING_APPROVAL",
                },
            }

        # Permission GRANTED: Execute under sandbox
        try:
            result = tool.execute(**kwargs)
            if not isinstance(result, dict):
                result = {"handled": True, "result": result}

            result["tool"] = name
            result["risk_level"] = tool.risk_level.value

            # Post-execution verification if defined
            if tool.verify:
                try:
                    verified = tool.verify(result, **kwargs)
                    result["verified"] = bool(verified)
                except Exception as ve:
                    logger.debug(f"Verification check error for '{name}': {ve}")
                    result["verified"] = False
            else:
                result["verified"] = True

            audit_logger.log_event(
                event_type="TOOL_EXECUTED",
                risk_level=tool.risk_level.value,
                target=name,
                decision="SUCCESS",
                reason=f"Executed tool '{name}' successfully",
                provenance=provenance.value,
                details={"verified": result.get("verified", True)},
            )

            return result
        except Exception as exc:
            logger.error(f"Error executing tool '{name}': {exc}", exc_info=True)
            audit_logger.log_event(
                event_type="TOOL_EXECUTION_ERROR",
                risk_level=tool.risk_level.value,
                target=name,
                decision="ERROR",
                reason=str(exc),
                provenance=provenance.value,
            )
            return {
                "handled": True,
                "success": False,
                "error": str(exc),
                "tool": name,
            }


# Global tool registry instance
tool_registry = ToolRegistry()
