"""
Unit tests for AURA Action Planner, Tool Registry, File Manager, and Dev Assistant services.
"""

import unittest
from backend.services.tool_registry import tool_registry, ToolDefinition, RiskLevel
from backend.services.action_planner import ActionPlanner
from backend.services.file_manager_service import FileManagerService
from backend.services.dev_assistant_service import DevAssistantService


class TestActionPlannerAndRegistry(unittest.TestCase):
    def setUp(self):
        ActionPlanner.initialize_registry()

    def test_tool_registry_registration_and_list(self):
        tools = tool_registry.list_tools()
        names = [t["name"] for t in tools]
        self.assertIn("launch_app", names)
        self.assertIn("close_app", names)
        self.assertIn("organize_downloads", names)
        self.assertIn("git_status", names)
        self.assertIn("storage_drives", names)

    def test_tool_registry_execution_verification(self):
        def sample_exec(x: int):
            return {"result": x * 2}

        tool_registry.register(ToolDefinition(
            name="test_multiplier",
            description="Multiplies number by two",
            category="Test",
            risk_level=RiskLevel.LOW,
            execute=sample_exec,
            verify=lambda res, x: res.get("result") == x * 2,
        ))

        res = tool_registry.execute("test_multiplier", x=5)
        self.assertTrue(res.get("verified"))
        self.assertEqual(res.get("result"), 10)

    def test_file_manager_storage_drives(self):
        drives = FileManagerService.get_storage_drives()
        self.assertTrue(drives.get("handled"))
        self.assertIn("drives", drives.get("data", {}))
        self.assertGreater(len(drives["data"]["drives"]), 0)

    def test_file_manager_organize_preview(self):
        preview = FileManagerService.organize_downloads(preview=True)
        self.assertTrue(preview.get("handled"))
        self.assertTrue(preview.get("data", {}).get("preview"))
        self.assertIn("plan", preview.get("data", {}))

    def test_dev_assistant_git_status(self):
        status = DevAssistantService.get_git_status()
        self.assertTrue(status.get("handled"))
        self.assertIn("is_git", status.get("data", {}))

    def test_action_planner_single_intents(self):
        # 1. Active window
        res_win = ActionPlanner.plan_and_execute("what is the active window")
        self.assertIsNotNone(res_win)
        self.assertTrue(res_win.get("handled"))

        # 2. Storage usage
        res_stor = ActionPlanner.plan_and_execute("storage usage")
        self.assertIsNotNone(res_stor)
        self.assertTrue(res_stor.get("handled"))
        self.assertEqual(res_stor.get("action"), "storage_analysis")

        # 3. Organize downloads
        res_org = ActionPlanner.plan_and_execute("organize my downloads")
        self.assertIsNotNone(res_org)
        self.assertEqual(res_org.get("action"), "file_organize")

        # 4. YouTube search
        res_yt = ActionPlanner.plan_and_execute("search youtube for classical music")
        self.assertIsNotNone(res_yt)
        self.assertEqual(res_yt.get("action"), "web_search")
        self.assertEqual(res_yt.get("data", {}).get("platform"), "youtube")

    def test_action_planner_multi_step_workflow(self):
        compound = ActionPlanner.plan_and_execute("organize my downloads and check my battery")
        self.assertIsNotNone(compound)
        self.assertTrue(compound.get("handled"))
        self.assertEqual(compound.get("action"), "composite_workflow")
        self.assertEqual(compound.get("data", {}).get("step_count"), 2)


if __name__ == "__main__":
    unittest.main()
