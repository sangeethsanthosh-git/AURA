from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from backend.actions.executor import ActionExecutor
from backend.actions.manager import ActionManager
from backend.actions.models import ActionRequest, ActionResult, ActionType, TargetType
from backend.actions.planner import ActionPlanner
from backend.actions.registry import ApplicationEntry, ApplicationRegistry
from backend.actions.target_resolver import TargetResolver
from backend.agent.controller import TaskController
from backend.agent.models import TaskState
from backend.agent.planner import TaskPlanner
from backend.router.math_engine import MathEngine
from backend.router.intent_classifier import IntentClassifier
from backend.router.intent_types import Intent
from backend.router.smart_router import SmartRouter
from backend.vision.models import ActionVerificationResult
from backend.vision.verification import ActionVerifier


class HandsTaskUnderstandingTest(unittest.TestCase):
    def test_application_resolution_normalizes_calculator_variants(self) -> None:
        resolver = TargetResolver()
        for phrase in ("calculator", "calculator app", "the calculator application"):
            resolved = resolver.resolve(phrase, TargetType.APPLICATION)
            self.assertEqual(resolved.target_type, TargetType.APPLICATION)
            self.assertEqual(resolved.target, "calculator")

    def test_spotify_app_prefers_application_without_website_fallback(self) -> None:
        action = ActionPlanner().plan("open spotify app")[0]
        self.assertEqual(action.action_type, ActionType.OPEN_APPLICATION)
        self.assertEqual(action.target, "spotify")

    def test_spotify_website_resolves_to_website(self) -> None:
        action = ActionPlanner().plan("open spotify website")[0]
        self.assertEqual(action.action_type, ActionType.OPEN_WEBSITE)
        self.assertEqual(action.target, "https://open.spotify.com/")

    def test_bare_spotify_uses_website_when_app_not_launchable(self) -> None:
        with patch.object(ApplicationRegistry, "launch_command", return_value=None):
            action = ActionPlanner().plan("open spotify")[0]
        self.assertEqual(action.action_type, ActionType.OPEN_WEBSITE)

    def test_google_chrome_and_vscode_aliases_resolve(self) -> None:
        planner = ActionPlanner()
        chrome = planner.plan("open google chrome")[0]
        vscode = planner.plan("open vs code")[0]
        self.assertEqual(chrome.target, "chrome")
        self.assertEqual(vscode.target, "vscode")

    def test_unknown_application_returns_clear_failure(self) -> None:
        result = ActionExecutor(ApplicationRegistry(())).execute(ActionRequest(ActionType.OPEN_APPLICATION, "missing app"))
        self.assertFalse(result.success)
        self.assertIn("do not know", result.message)

    def test_target_resolution_types(self) -> None:
        resolver = TargetResolver()
        self.assertEqual(resolver.resolve("calculator", TargetType.APPLICATION).target_type, TargetType.APPLICATION)
        self.assertEqual(resolver.resolve("spotify website").target_type, TargetType.WEBSITE)
        self.assertEqual(resolver.resolve("https://example.com").target_type, TargetType.URL)
        self.assertEqual(resolver.resolve("C:\\test.pdf").target_type, TargetType.FILE)
        self.assertEqual(resolver.resolve("Downloads folder").target_type, TargetType.FOLDER)

    def test_calculator_addition_decomposes_to_open_and_calculate(self) -> None:
        actions = [step.action for step in TaskPlanner().plan("open calculator and add 5 and 6").steps]
        self.assertEqual([action.action_type for action in actions], [ActionType.OPEN_APPLICATION, ActionType.CALCULATE])
        self.assertEqual(actions[1].target, "5 + 6")

    def test_calculator_then_calculate_decomposes_to_two_actions(self) -> None:
        actions = [step.action.action_type for step in TaskPlanner().plan("open calculator then calculate 5 + 6").steps]
        self.assertEqual(actions, [ActionType.OPEN_APPLICATION, ActionType.CALCULATE])

    def test_chrome_search_decomposes_to_multiple_actions(self) -> None:
        actions = [step.action.action_type for step in TaskPlanner().plan("open chrome and search Python tutorials").steps]
        self.assertEqual(actions, [ActionType.OPEN_APPLICATION, ActionType.WEB_SEARCH])

    def test_notepad_write_decomposes_to_open_and_type(self) -> None:
        actions = [step.action.action_type for step in TaskPlanner().plan("open notepad and write hello").steps]
        self.assertEqual(actions, [ActionType.OPEN_APPLICATION, ActionType.TYPE_TEXT])

    def test_spotify_play_decomposes_to_open_and_play_media(self) -> None:
        actions = [step.action for step in TaskPlanner().plan("open spotify and play").steps]
        self.assertEqual([action.action_type for action in actions], [ActionType.OPEN_APPLICATION, ActionType.PLAY_MEDIA])
        self.assertEqual(actions[1].target, "spotify")

    def test_play_spotify_plans_media_action(self) -> None:
        actions = [step.action for step in TaskPlanner().plan("play spotify").steps]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].action_type, ActionType.PLAY_MEDIA)
        self.assertEqual(actions[0].target, "spotify")

    def test_close_vscode_plans_unsupported_close_action(self) -> None:
        actions = [step.action for step in TaskPlanner().plan("close vscode").steps]
        self.assertEqual(actions[0].action_type, ActionType.CLOSE_APPLICATION)
        self.assertEqual(actions[0].target, "vscode")

    def test_open_file_is_ambiguous_not_application(self) -> None:
        plan = TaskPlanner().plan("open file")
        self.assertEqual(plan.steps[0].action.action_type, ActionType.BLOCKED)
        self.assertEqual(plan.steps[0].action.parameters["ambiguity"], "missing_target")

    def test_open_file_path_is_open_file(self) -> None:
        action = ActionPlanner().plan("open C:\\test.pdf")[0]
        self.assertEqual(action.action_type, ActionType.OPEN_FILE)
        self.assertEqual(action.target, "C:\\test.pdf")

    def test_play_media_executor_reports_not_implemented(self) -> None:
        action = ActionRequest(ActionType.PLAY_MEDIA, "spotify")
        result = ActionExecutor().execute(action)
        self.assertFalse(result.success)
        self.assertEqual(result.to_response_data()["status"], "not_implemented")
        self.assertIn("not available yet", result.message)

    def test_open_spotify_and_play_reports_partial_truth(self) -> None:
        executor = Mock()

        def execute(action):
            if action.action_type == ActionType.OPEN_APPLICATION:
                return ActionResult(True, action.action_id, action.action_type, "Opened Spotify.", "fake", action.target, 0, status="success")
            return ActionResult(False, action.action_id, action.action_type, "spotify is targeted, but media playback control is not available yet.", "fake", action.target, 0, error="not implemented", status="not_implemented")

        executor.execute.side_effect = execute
        action_manager = ActionManager(executor=executor, logger=Mock(), verifier=Mock())
        action_manager.verifier.verify.return_value = None
        response = TaskController(action_manager, max_retries_per_step=0, max_total_retries=0).handle("open spotify and play")
        self.assertFalse(response["ok"])
        self.assertIn("Opened Spotify", response["error"]["message"])
        self.assertIn("media playback control is not available", response["error"]["message"])

    def test_failed_prerequisite_stops_dependent_calculation(self) -> None:
        executor = Mock()
        executor.execute.side_effect = lambda action: ActionResult(
            action.action_type != ActionType.OPEN_APPLICATION,
            action.action_id,
            action.action_type,
            "failed" if action.action_type == ActionType.OPEN_APPLICATION else "done",
            "fake",
            action.target,
            0,
            "failed" if action.action_type == ActionType.OPEN_APPLICATION else None,
        )
        action_manager = ActionManager(executor=executor, logger=Mock(), verifier=Mock())
        action_manager.verifier.verify.return_value = None
        response = TaskController(action_manager, max_retries_per_step=0, max_total_retries=0).handle("open calculator and add 5 and 6")
        self.assertFalse(response["ok"])
        self.assertEqual(executor.execute.call_count, 1)

    def test_failed_open_spotify_stops_play_media(self) -> None:
        executor = Mock()
        executor.execute.side_effect = lambda action: ActionResult(False, action.action_id, action.action_type, "Spotify unavailable.", "fake", action.target, 0, "failed", status="failed")
        action_manager = ActionManager(executor=executor, logger=Mock(), verifier=Mock())
        action_manager.verifier.verify.return_value = None
        response = TaskController(action_manager, max_retries_per_step=0, max_total_retries=0).handle("open spotify and play")
        self.assertFalse(response["ok"])
        self.assertEqual(executor.execute.call_count, 1)

    def test_calculate_uses_deterministic_math_engine(self) -> None:
        executor = ActionExecutor()
        with patch.object(executor.math_engine, "solve", wraps=executor.math_engine.solve) as solve:
            result = executor.execute(ActionRequest(ActionType.CALCULATE, "587 * 932", {"expression": "587 * 932"}))
        self.assertTrue(result.success)
        self.assertEqual(result.metadata["result"], 547084)
        solve.assert_called_once()

    def test_math_engine_results(self) -> None:
        engine = MathEngine()
        self.assertEqual(engine.solve("5 + 6")["data"]["result"], 11)
        self.assertEqual(engine.solve("25 * 4")["data"]["result"], 100)
        self.assertEqual(engine.solve("587 * 932")["data"]["result"], 547084)

    def test_no_vision_provider_reports_not_available(self) -> None:
        verifier = ActionVerifier()
        verifier.vision_manager.provider.is_available = Mock(return_value=False)
        action = ActionRequest(ActionType.OPEN_APPLICATION, "calculator")
        result = ActionResult(True, action.action_id, action.action_type, "Opened Calculator.", "fake", action.target, 0)
        verification = verifier.verify(action, result)
        self.assertIsNotNone(verification)
        self.assertEqual(verification.safe_dict()["verification_status"], "not_available")
        self.assertIn("skipped", verification.observed.lower())

    def test_folder_target_resolution_with_real_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            resolved = TargetResolver().resolve(str(path), TargetType.FOLDER)
            self.assertEqual(resolved.target_type, TargetType.FOLDER)

    def test_computer_media_intent_does_not_fall_through_to_ollama(self) -> None:
        result = IntentClassifier().classify("play spotify")
        self.assertEqual(result.intent, Intent.COMPUTER_ACTIONS)

    def test_unknown_computer_action_routes_to_hands_not_ollama_claim(self) -> None:
        router = SmartRouter()
        router.service_manager.ask = Mock()
        response = router.ask("close vscode")
        self.assertFalse(response["ok"])
        router.service_manager.ask.assert_not_called()


if __name__ == "__main__":
    unittest.main()
