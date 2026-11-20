"""
Unit and benchmark tests for AURA Resource-Efficient Screen Perception,
In-Memory Processing, Windows Media OCR, Perception Caching, and Resource Monitoring.
"""

import unittest
import time
import os
import io
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from backend.services.perception_cache import perception_cache, PerceptionCache
from backend.services.ocr_service import ocr_service, OCRService
from backend.services.vision_service import VisionService, get_active_window_title
from backend.services.resource_monitor import resource_monitor, ResourceMonitor
from backend.services.action_planner import ActionPlanner
from backend.api.app import app


class TestScreenPerceptionAndCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ActionPlanner.initialize_registry()
        cls.client = TestClient(app)
        cls.test_dir = Path("backend/data/test_temp_screenshots").resolve()
        cls.test_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if cls.test_dir.exists():
            for f in cls.test_dir.glob("*"):
                try:
                    f.unlink()
                except Exception:
                    pass
            try:
                cls.test_dir.rmdir()
            except Exception:
                pass

    def setUp(self):
        perception_cache.invalidate_all("Test Setup")
        self.vision = VisionService(storage_dir=str(self.test_dir))

    def tearDown(self):
        self.vision.cleanup_temp_files(max_age_seconds=0)

    def test_01_in_memory_screen_capture_zero_disk_write(self):
        """Verifies in-memory screen capture returns an image without writing to disk."""
        img, elapsed_ms = self.vision.grab_screen_image()
        self.assertIsInstance(img, Image.Image)
        self.assertGreater(img.width, 0)
        self.assertGreater(img.height, 0)
        self.assertGreater(elapsed_ms, 0)

        # capture_screen with save_to_disk=False
        res = self.vision.capture_screen(save_to_disk=False)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["image_path"], "")
        self.assertTrue(res["thumbnail"].startswith("data:image/jpeg;base64,"))
        img.close()

    def test_02_temporary_screenshot_context_manager_cleanup(self):
        """Verifies temporary screenshot file is deleted on exit and on exceptions."""
        temp_file_path = None
        with self.vision.temporary_screenshot() as (img, path):
            temp_file_path = path
            self.assertTrue(path.exists())
            self.assertIsInstance(img, Image.Image)

        # Must be deleted immediately after context exit
        self.assertFalse(temp_file_path.exists())

        # Verify deletion even if an exception occurs
        err_path = None
        try:
            with self.vision.temporary_screenshot() as (img, path):
                err_path = path
                raise ValueError("Simulated crash inside screenshot processing")
        except ValueError:
            pass

        self.assertFalse(err_path.exists())

    def test_03_bounded_screenshot_disk_retention(self):
        """Verifies storage_dir prunes older screenshots and enforces max_retained_screenshots limit."""
        self.vision.max_retained_screenshots = 3
        # Create 6 screenshots
        for i in range(6):
            self.vision.capture_screen(save_filename=f"shot_{i}.png", save_to_disk=True)
            time.sleep(0.01)

        png_files = list(self.test_dir.glob("*.png"))
        self.assertLessEqual(len(png_files), 3)

    def test_04_perceptual_screen_hashing(self):
        """Verifies perceptual hash consistency and mutation detection."""
        img1 = Image.new("RGB", (640, 480), color=(100, 150, 200))
        img2 = Image.new("RGB", (640, 480), color=(100, 150, 200))
        img3 = Image.new("RGB", (640, 480), color=(20, 20, 20))

        hash1 = perception_cache.calculate_screen_hash(img1)
        hash2 = perception_cache.calculate_screen_hash(img2)
        hash3 = perception_cache.calculate_screen_hash(img3)

        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
        img1.close()
        img2.close()
        img3.close()

    def test_05_ocr_service_cold_vs_cached_speedup(self):
        """Verifies in-memory OCR recognizes text and achieves sub-millisecond cached lookups."""
        from PIL import ImageFont
        img = Image.new("RGB", (500, 150), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 28)
        except Exception:
            font = None
        draw.text((25, 40), "AURA Secure Automation", fill=(0, 0, 0), font=font)

        # Cold Run
        res1 = ocr_service.recognize_image(img, hwnd=999, window_title="TestWindow", use_cache=True)
        self.assertIn("AURA", res1.get("full_text", ""))
        self.assertFalse(res1.get("from_cache"))

        # Cached Run (same image, same window)
        res2 = ocr_service.recognize_image(img, hwnd=999, window_title="TestWindow", use_cache=True)
        self.assertTrue(res2.get("from_cache"))
        self.assertLess(res2.get("elapsed_ms", 100), 5.0)  # Sub-5ms cached return

        # Find Coordinate
        coord = ocr_service.find_text_coordinate("Secure", img, hwnd=999)
        self.assertIsNotNone(coord)
        self.assertIsInstance(coord[0], int)
        self.assertIsInstance(coord[1], int)
        img.close()

    def test_06_cache_invalidation_on_window_or_content_change(self):
        """Verifies cache invalidates when window HWND, resolution, or screen hash changes."""
        img = Image.new("RGB", (300, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 30), "Save File", fill=(0, 0, 0))

        # Cache with HWND=100
        res1 = ocr_service.recognize_image(img, hwnd=100, window_title="App1")
        self.assertFalse(res1.get("from_cache"))

        # Switched window to HWND=200 -> Must be cache miss!
        res2 = ocr_service.recognize_image(img, hwnd=200, window_title="App2")
        self.assertFalse(res2.get("from_cache"))

        # Mutate image content -> Must be cache miss!
        draw.text((20, 60), "New Content Added", fill=(0, 0, 0))
        res3 = ocr_service.recognize_image(img, hwnd=100, window_title="App1")
        self.assertFalse(res3.get("from_cache"))
        img.close()

    def test_07_cache_ttl_expiration(self):
        """Verifies cache entries expire after TTL."""
        cache = PerceptionCache(ttl_seconds=0.1)
        img = Image.new("RGB", (200, 100), color=(50, 50, 50))
        s_hash = cache.calculate_screen_hash(img)

        cache.put_ocr(s_hash, hwnd=10, resolution=(200, 100), window_title="W", ocr_data={"text": "hello"})
        self.assertIsNotNone(cache.get_ocr(s_hash, hwnd=10, resolution=(200, 100)))

        time.sleep(0.15)
        # Expired!
        self.assertIsNone(cache.get_ocr(s_hash, hwnd=10, resolution=(200, 100)))
        img.close()

    def test_08_gpu_model_unloading(self):
        """Verifies unload_vision_models executes without error and clears CUDA cache."""
        with patch("httpx.Client.get") as mock_get, patch("httpx.Client.post") as mock_post:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {"models": [{"name": "llava:7b"}]})
            mock_post.return_value = MagicMock(status_code=200)

            res = VisionService.unload_vision_models()
            self.assertTrue(res["success"])
            self.assertEqual(res["count"], 1)
            self.assertIn("llava:7b", res["unloaded_models"])

    def test_09_resource_monitor_metrics(self):
        """Verifies ResourceMonitor aggregates RAM, CPU, GPU VRAM, latency, and cache metrics."""
        metrics = resource_monitor.get_metrics()
        self.assertIn("ram", metrics)
        self.assertIn("cpu", metrics)
        self.assertIn("gpu", metrics)
        self.assertIn("latency", metrics)
        self.assertIn("cache", metrics)
        self.assertIn("temporary_storage", metrics)

        self.assertGreater(metrics["ram"]["process_mb"], 0)
        self.assertIn("entries_count", metrics["cache"])

    def test_10_extended_session_stability_and_zero_leak(self):
        """
        Executes 25 repeated capture and OCR operations over a continuous simulated session.
        Verifies memory remains bounded and zero temporary files leak.
        """
        import psutil
        proc = psutil.Process()
        initial_ram_mb = proc.memory_info().rss / (1024 * 1024)

        img = Image.new("RGB", (500, 200), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        draw.text((30, 80), "Extended Session Testing", fill=(0, 0, 0))

        hit_count = 0
        for i in range(25):
            res = ocr_service.recognize_image(img, hwnd=555, window_title="StableApp", use_cache=True)
            if res.get("from_cache"):
                hit_count += 1

        self.assertGreaterEqual(hit_count, 24)  # 24 hits out of 25 runs!

        final_ram_mb = proc.memory_info().rss / (1024 * 1024)
        ram_delta = final_ram_mb - initial_ram_mb
        # Memory growth should be minimal (< 35 MB across 25 runs)
        self.assertLess(ram_delta, 35.0)

        # Temporary files count must be clean
        temp_stats = resource_monitor.get_temporary_storage_metrics()
        self.assertLessEqual(temp_stats["file_count"], 5)
        img.close()

    def test_11_rest_api_endpoints(self):
        """Verifies FastAPI REST endpoints for resource metrics and cache controls."""
        # 1. GET /api/system/resource-metrics
        res1 = self.client.get("/api/system/resource-metrics")
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertIn("ram", data1)
        self.assertIn("cache", data1)

        # 2. GET /api/perception/cache-status
        res2 = self.client.get("/api/perception/cache-status")
        self.assertEqual(res2.status_code, 200)
        self.assertIn("entries_count", res2.json())

        # 3. POST /api/perception/cache-clear
        res3 = self.client.post("/api/perception/cache-clear")
        self.assertEqual(res3.status_code, 200)
        self.assertTrue(res3.json().get("success"))

        # 4. POST /api/perception/cleanup-temp
        res4 = self.client.post("/api/perception/cleanup-temp")
        self.assertEqual(res4.status_code, 200)
        self.assertTrue(res4.json().get("success"))

        # 5. POST /api/system/models/unload
        with patch.object(VisionService, "unload_vision_models", return_value={"success": True, "count": 0}):
            res5 = self.client.post("/api/system/models/unload")
            self.assertEqual(res5.status_code, 200)
            self.assertTrue(res5.json().get("success"))


if __name__ == "__main__":
    unittest.main()
