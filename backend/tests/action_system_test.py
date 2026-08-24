from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from backend.actions.executor import ActionExecutor
from backend.actions.logger import ActionLogger
from backend.actions.manager import ActionManager
from backend.actions.models import ActionRequest, ActionType, RiskLevel
from backend.actions.permissions import PermissionManager
from backend.actions.planner import ActionPlanner
from backend.actions.registry import ApplicationEntry, ApplicationRegistry
from backend.router.intent_classifier import IntentClassifier
from backend.router.intent_types import Intent
from backend.router.smart_router import SmartRouter


class ActionSystemTest(unittest.TestCase):
    def test_open_registered_application(self) -> None:
        registry = ApplicationRegistry((ApplicationEntry("demo", "Demo App", ("demo",), ("demo.exe",)),))
        executor = ActionExecutor(registry)
        with patch.object(registry, "launch_command", return_value="demo.exe"), patch("backend.actions.executor.subprocess.Popen") as popen:
            result = executor.execute(ActionRequest(ActionType.OPEN_APPLICATION, "demo"))
        self.assertTrue(result.success)
        popen.assert_called_once()

    def test_unknown_application(self) -> None:
        result = ActionExecutor(ApplicationRegistry(())).execute(ActionRequest(ActionType.OPEN_APPLICATION, "missing"))
        self.assertFalse(result.success)
        self.assertIn("do not know", result.message)

    def test_application_unavailable(self) -> None:
        registry = ApplicationRegistry((ApplicationEntry("demo", "Demo App", ("demo",), ("demo.exe",)),))
        with patch.object(registry, "launch_command", return_value=None):
            result = ActionExecutor(registry).execute(ActionRequest(ActionType.OPEN_APPLICATION, "demo"))
        self.assertFalse(result.success)
        self.assertIn("not available", result.message)

    def test_open_known_website(self) -> None:
        action = ActionPlanner().plan("Open YouTube.")[0]
        self.assertEqual(action.action_type, ActionType.OPEN_WEBSITE)
        self.assertEqual(action.target, "https://www.youtube.com/")

    def test_invalid_url_rejection(self) -> None:
        self.assertEqual(ActionPlanner().plan("Open https://bad url"), [])

    def test_google_search_url_generation(self) -> None:
        action = ActionPlanner().plan("Search Google for Python machine learning tutorials.")[0]
        self.assertEqual(action.action_type, ActionType.WEB_SEARCH)
        self.assertIn("Python+machine+learning+tutorials", action.parameters["url"])

    def test_safe_action_executes_without_confirmation(self) -> None:
        executor = Mock()
        executor.execute.return_value = self._result(True)
        manager = ActionManager(executor=executor, logger=Mock())
        with patch("backend.actions.executor.webbrowser.open", return_value=True):
            response = manager.handle("Open YouTube")
        self.assertTrue(response["ok"])
        executor.execute.assert_called_once()

    def test_folder_creation_requires_confirmation(self) -> None:
        action = ActionPlanner().plan("Create a folder called Research")[0]
        decision = PermissionManager().check_permission(action)
        self.assertEqual(decision.value, "confirm_required")

    def test_action_does_not_execute_before_confirmation(self) -> None:
        executor = Mock()
        manager = ActionManager(executor=executor, logger=Mock())
        response = manager.handle("Create a folder called Research")
        self.assertTrue(response["ok"])
        self.assertEqual(response["action"], "confirmation_required")
        executor.execute.assert_not_called()

    def test_confirm_executes_only_pending_action(self) -> None:
        executor = Mock()
        executor.execute.return_value = self._result(True)
        manager = ActionManager(executor=executor, logger=Mock())
        manager.handle("Create a folder called Research")
        manager.confirm_pending()
        second = manager.confirm_pending()
        self.assertEqual(executor.execute.call_count, 1)
        self.assertFalse(second["ok"])

    def test_cancel_clears_pending_action(self) -> None:
        executor = Mock()
        manager = ActionManager(executor=executor, logger=Mock())
        manager.handle("Create a folder called Research")
        manager.cancel_pending()
        manager.confirm_pending()
        executor.execute.assert_not_called()

    def test_expired_confirmation_cannot_execute(self) -> None:
        executor = Mock()
        manager = ActionManager(executor=executor, logger=Mock(), confirmation_ttl_seconds=0)
        manager.handle("Create a folder called Research")
        time.sleep(0.01)
        response = manager.confirm_pending()
        self.assertFalse(response["ok"])
        executor.execute.assert_not_called()

    def test_file_rename_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "report.txt"
            destination = root / "final.txt"
            source.write_text("a", encoding="utf-8")
            destination.write_text("b", encoding="utf-8")
            result = ActionExecutor().execute(ActionRequest(ActionType.RENAME_FILE, str(source), {"new_name": "final.txt"}))
        self.assertFalse(result.success)
        self.assertIn("already exists", result.message)

    def test_copy_file_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "report.txt"
            destination = root / "copy.txt"
            source.write_text("a", encoding="utf-8")
            destination.write_text("b", encoding="utf-8")
            result = ActionExecutor().execute(ActionRequest(ActionType.COPY_FILE, str(source), {"destination": str(destination)}))
        self.assertFalse(result.success)
        self.assertIn("already exists", result.message)

    def test_move_file_with_invalid_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "report.txt"
            source.write_text("a", encoding="utf-8")
            result = ActionExecutor().execute(ActionRequest(ActionType.MOVE_FILE, str(source), {"destination": str(root / "missing" / "report.txt")}))
        self.assertFalse(result.success)
        self.assertIn("Destination folder does not exist", result.message)

    def test_blocked_action_is_rejected(self) -> None:
        response = ActionManager(logger=Mock()).handle("Delete file report.txt")
        self.assertFalse(response["ok"])
        self.assertIn("blocked", response["error"]["message"])

    def test_llm_generated_invalid_action_schema_is_rejected(self) -> None:
        suggestion = {"action_type": "open_application", "application": "chrome", "command": "rm -rf /"}
        self.assertIsNone(ActionPlanner().validate_llm_suggestion(suggestion))

    def test_no_arbitrary_shell_command_execution_path_exists(self) -> None:
        response = ActionManager(logger=Mock()).handle("Run command dir")
        self.assertFalse(response["ok"])
        self.assertIn("blocked", response["error"]["message"])

    def test_action_result_reports_failure(self) -> None:
        response = ActionManager(logger=Mock()).handle("Open TotallyMissingApp")
        self.assertFalse(response["ok"])

    def test_action_log_records_without_sensitive_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            log_path = Path(temp) / "actions.jsonl"
            logger = ActionLogger(log_path)
            action = ActionRequest(ActionType.OPEN_WEBSITE, "https://example.com", {"password": "secret"})
            logger.log(action, self._result(True, action))
            record = json.loads(log_path.read_text(encoding="utf-8").strip())
        self.assertNotIn("password", record)
        self.assertEqual(record["target"], "https://example.com")

    def test_classifier_routes_open_chrome_to_computer_actions(self) -> None:
        result = IntentClassifier().classify("Open Chrome")
        self.assertEqual(result.intent, Intent.COMPUTER_ACTIONS)

    def test_router_confirmation_flow(self) -> None:
        router = SmartRouter()
        router.action_manager.executor = Mock()
        router.action_manager.executor.execute.return_value = self._result(True)
        router.action_manager.logger = Mock()
        router.action_manager.verifier = Mock()
        router.action_manager.verifier.verify.return_value = None
        first = router.ask("Create a folder called Research")
        second = router.ask("yes")
        self.assertEqual(first["action"], "confirmation_required")
        self.assertTrue(second["ok"])

    @staticmethod
    def _result(success: bool, action: ActionRequest | None = None):
        from backend.actions.models import ActionResult

        request = action or ActionRequest(ActionType.OPEN_WEBSITE, "https://example.com")
        return ActionResult(success, request.action_id, request.action_type, "done" if success else "failed", "test", request.target, 0.0, None if success else "failed")


if __name__ == "__main__":
    unittest.main()
