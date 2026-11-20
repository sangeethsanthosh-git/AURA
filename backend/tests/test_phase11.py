import unittest
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient
from backend.api.app import app


class TestPhase11SystemTrayAndHotkey(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.project_root = Path(__file__).resolve().parent.parent.parent

    def test_01_tray_icon_and_scripts_exist(self):
        main_cjs = self.project_root / "frontend" / "electron" / "main.cjs"
        preload_cjs = self.project_root / "frontend" / "electron" / "preload.cjs"
        tray_icon = self.project_root / "frontend" / "electron" / "tray_icon.png"

        self.assertTrue(main_cjs.exists(), "main.cjs must exist")
        self.assertTrue(preload_cjs.exists(), "preload.cjs must exist")
        self.assertTrue(tray_icon.exists(), "tray_icon.png must exist")

        # Verify tray icon is a valid image
        with Image.open(tray_icon) as img:
            self.assertGreaterEqual(img.width, 16)
            self.assertGreaterEqual(img.height, 16)
            self.assertEqual(img.format, "PNG")

    def test_02_main_cjs_tray_and_hotkey_features(self):
        main_cjs = self.project_root / "frontend" / "electron" / "main.cjs"
        content = main_cjs.read_text(encoding="utf-8")

        # Test required Phase 11 keywords
        self.assertIn("Tray", content)
        self.assertIn("globalShortcut", content)
        self.assertIn("CommandOrControl+Shift+Space", content)
        self.assertIn("createTray", content)
        self.assertIn("mainWindow.hide()", content)
        self.assertIn("isQuitting", content)
        self.assertIn("requestSingleInstanceLock", content)

    def test_03_preload_bridge_features(self):
        preload_cjs = self.project_root / "frontend" / "electron" / "preload.cjs"
        content = preload_cjs.read_text(encoding="utf-8")

        self.assertIn("onGlobalHotkey", content)
        self.assertIn("showWindow", content)
        self.assertIn("hideWindow", content)

    def test_04_system_api_endpoints_health(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("vision_ready"))
        self.assertIn("rag_chunks", data)
        self.assertIn("active_reminders", data)

    def test_05_documents_and_reminders_endpoints(self):
        # Documents endpoint
        resp_docs = self.client.get("/api/documents")
        self.assertEqual(resp_docs.status_code, 200)
        docs_data = resp_docs.json()
        self.assertIn("documents", docs_data)
        self.assertIn("chunk_count", docs_data)

        # Reminders endpoint
        resp_rems = self.client.get("/api/reminders")
        self.assertEqual(resp_rems.status_code, 200)
        rems_data = resp_rems.json()
        self.assertIn("reminders", rems_data)

    def test_06_desktop_launchers_and_setup_wizard(self):
        # 1. Verify launcher scripts exist
        bat_file = self.project_root / "Launch_AURA_Desktop.bat"
        vbs_file = self.project_root / "Launch_AURA_Desktop.vbs"
        wizard_file = self.project_root / "frontend" / "src" / "components" / "SetupWizard.tsx"

        self.assertTrue(bat_file.exists(), "Launch_AURA_Desktop.bat must exist")
        self.assertTrue(vbs_file.exists(), "Launch_AURA_Desktop.vbs must exist")
        self.assertTrue(wizard_file.exists(), "SetupWizard.tsx must exist")

        # 2. Check wizard contents
        wizard_code = wizard_file.read_text(encoding="utf-8")
        self.assertIn("SetupWizard", wizard_code)
        self.assertIn("diagnostics", wizard_code)
        self.assertIn("clara", wizard_code)
        self.assertIn("micLevel", wizard_code)
        self.assertIn("aura_setup_completed", wizard_code)


if __name__ == "__main__":
    unittest.main()
