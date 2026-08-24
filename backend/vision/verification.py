"""Bounded Eyes verification for selected Hands actions."""

from __future__ import annotations

from pathlib import Path

from backend.actions.models import ActionRequest, ActionResult, ActionType
from backend.vision.manager import VisionManager
from backend.vision.models import ActionVerificationResult, ScreenAnalysisTask


class ActionVerifier:
    VISUAL_ACTIONS = {ActionType.OPEN_APPLICATION, ActionType.OPEN_WEBSITE, ActionType.WEB_SEARCH}
    FILESYSTEM_ACTIONS = {ActionType.CREATE_FOLDER, ActionType.RENAME_FILE, ActionType.COPY_FILE, ActionType.MOVE_FILE}

    def __init__(self, vision_manager: VisionManager | None = None) -> None:
        self.vision_manager = vision_manager or VisionManager()

    def verify(self, action: ActionRequest, result: ActionResult) -> ActionVerificationResult | None:
        if not result.success:
            return None
        if action.action_type in self.FILESYSTEM_ACTIONS:
            return self._filesystem_verification(action)
        if action.action_type not in self.VISUAL_ACTIONS:
            return None
        if not self.vision_manager.provider.is_available():
            return ActionVerificationResult(
                action.action_id,
                False,
                "Visual verification skipped because no local vision model is available.",
                self._expected_state(action),
                None,
                "Provider capability check",
                "vision_unavailable",
                "No local vision model detected.",
                "not_available",
            )
        response = self.vision_manager.analyze_screen(
            f"Verify this expected screen state: {self._expected_state(action)}",
            ScreenAnalysisTask.ACTION_VERIFICATION,
        )
        ok = bool(response.get("ok"))
        observed = response.get("message") or (response.get("error") or {}).get("message") or ""
        return ActionVerificationResult(
            action.action_id,
            ok,
            str(observed),
            self._expected_state(action),
            None,
            "One-shot screen analysis",
            "AURA EYES",
            None if ok else str(observed),
            "verified" if ok else "failed",
        )

    @staticmethod
    def _filesystem_verification(action: ActionRequest) -> ActionVerificationResult:
        target = Path(action.target).expanduser()
        expected = "Filesystem target exists"
        success = False
        if action.action_type == ActionType.CREATE_FOLDER:
            success = target.is_dir()
            expected = f"Folder exists: {target}"
        elif action.action_type in {ActionType.COPY_FILE, ActionType.MOVE_FILE}:
            destination = Path(str(action.parameters.get("destination", ""))).expanduser()
            success = destination.exists()
            expected = f"Destination exists: {destination}"
        elif action.action_type == ActionType.RENAME_FILE:
            new_name = str(action.parameters.get("new_name", ""))
            destination = target.with_name(new_name)
            success = destination.exists() and not target.exists()
            expected = f"Renamed file exists: {destination}"
        return ActionVerificationResult(
            action.action_id,
            success,
            "Verified through filesystem state." if success else "Expected filesystem state was not observed.",
            expected,
            None,
            "Filesystem",
            "filesystem",
            None if success else "filesystem_verification_failed",
            "verified" if success else "failed",
        )

    @staticmethod
    def _expected_state(action: ActionRequest) -> str:
        if action.action_type == ActionType.OPEN_APPLICATION:
            return f"{action.target} application window visible"
        if action.action_type == ActionType.OPEN_WEBSITE:
            return f"Website visible: {action.target}"
        if action.action_type == ActionType.WEB_SEARCH:
            return f"Search results visible for: {action.target}"
        return f"Action completed: {action.action_type.value}"
