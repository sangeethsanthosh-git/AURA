import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image
from backend.services.vision_service import VisionService, get_active_window_title


class TestPhase8Vision(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.vision = VisionService(storage_dir="backend/data/test_screenshots")

    def tearDown(self):
        # Clean test directory
        test_dir = Path("backend/data/test_screenshots")
        if test_dir.exists():
            for f in test_dir.glob("*"):
                try:
                    f.unlink()
                except Exception:
                    pass
            try:
                test_dir.rmdir()
            except Exception:
                pass

    def test_01_get_active_window_title(self):
        title = get_active_window_title()
        self.assertIsInstance(title, str)
        self.assertGreater(len(title), 0)

    @patch("mss.MSS")
    def test_02_capture_screen_mocked(self, mock_mss):
        # Create dummy image
        dummy_img = Image.new("RGB", (640, 480), color="blue")
        dummy_bytes = dummy_img.tobytes("raw", "BGRX")

        mock_sct_instance = MagicMock()
        mock_sct_instance.monitors = [{"width": 640, "height": 480}, {"width": 640, "height": 480}]
        mock_shot = MagicMock()
        mock_shot.size = (640, 480)
        mock_shot.bgra = dummy_bytes
        mock_sct_instance.grab.return_value = mock_shot
        mock_mss.return_value.__enter__.return_value = mock_sct_instance

        res = self.vision.capture_screen("test_mock.png")
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["thumbnail"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(res["width"], 640)
        self.assertEqual(res["height"], 480)
        self.assertTrue(Path(res["image_path"]).exists())

    @patch("httpx.AsyncClient.post")
    @patch("httpx.AsyncClient.get")
    async def test_03_analyze_screen_fallback(self, mock_get, mock_post):
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"models": []})
        mock_post.return_value = MagicMock(
            status_code=200, json=lambda: {"response": "I see your code editor open with App.tsx."}
        )

        test_img = self.vision.storage_dir / "temp.png"
        Image.new("RGB", (100, 100), color="white").save(test_img)

        result = await self.vision.analyze_screen(str(test_img), "What is on my screen?", "Visual Studio Code")
        self.assertIn("code editor", result.lower())


if __name__ == "__main__":
    unittest.main()
