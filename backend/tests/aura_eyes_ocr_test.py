from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.vision.capture import ScreenCaptureManager
from backend.vision.manager import VisionManager
from backend.vision.models import CaptureRegionType, ScreenAnalysisTask, ScreenCaptureResult
from backend.vision.ocr.base import OCRProvider, OCRRegion, OCRResult
from backend.vision.ocr.manager import OCRManager
from backend.vision.ocr.model_manager import OCRModelManager
from backend.vision.ocr.paths import OCR_TEMP_DIR, PROJECT_ROOT
from ui.controller.aura_controller import AuraController


class FakeOCRProvider(OCRProvider):
    provider_name = "Fake Malayalam OCR"

    def __init__(self, available: bool = True) -> None:
        self.available = available
        self.languages_seen: list[tuple[str, ...]] = []
        self.unload_calls = 0

    def is_available(self) -> bool:
        return self.available

    def supported_languages(self) -> tuple[str, ...]:
        return ("en", "ml", "mixed")

    def recognize(self, image_path: Path, languages: tuple[str, ...]) -> OCRResult:
        self.languages_seen.append(languages)
        if not self.available:
            return OCRResult(False, self.provider_name, languages=languages, error="Malayalam OCR is not currently available.")
        return OCRResult(
            True,
            self.provider_name,
            text="Settings\nനമസ്കാരം\nSave ചെയ്യുക",
            languages=languages,
            regions=(
                OCRRegion("Settings", 0.97, (10, 20, 110, 42), "en"),
                OCRRegion("നമസ്കാരം", 0.91, (10, 54, 160, 82), "ml"),
                OCRRegion("Save ചെയ്യുക", 0.89, (10, 94, 180, 124), "mixed"),
            ),
            confidence=0.923,
            model="fake-surya",
        )

    def unload(self) -> None:
        self.unload_calls += 1


class FakeCaptureManager:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.capture_calls = 0
        self.cleanup_calls = 0

    def capture_screen(self, monitor: int = 0, region_type=CaptureRegionType.FULL_SCREEN, region=None) -> ScreenCaptureResult:
        self.capture_calls += 1
        self.path.write_bytes(b"fake")
        return ScreenCaptureResult(True, 800, 600, temporary_path=self.path, metadata={"capture_latency_seconds": 0.001})

    def cleanup(self, capture: ScreenCaptureResult) -> bool:
        self.cleanup_calls += 1
        if capture.temporary_path and capture.temporary_path.exists():
            capture.temporary_path.unlink()
            return True
        return False


class AuraEyesOcrTest(unittest.TestCase):
    def test_ocr_manager_routes_malayalam_and_preserves_boxes_confidence(self) -> None:
        provider = FakeOCRProvider()
        manager = OCRManager(primary_provider=provider)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "screen.png"
            path.write_bytes(b"fake")
            result = manager.recognize_screen(path, "Read the Malayalam text on my screen.")

        self.assertTrue(result.success)
        self.assertEqual(provider.languages_seen[-1], ("ml", "en"))
        self.assertIn("നമസ്കാരം", result.visible_text or "")
        self.assertEqual(result.confidence, 0.923)
        self.assertEqual(result.elements[1].bounding_box, (10, 54, 160, 82))
        self.assertTrue(result.metadata["screen_text_is_untrusted"])

    def test_ocr_manager_routes_mixed_english_malayalam(self) -> None:
        provider = FakeOCRProvider()
        manager = OCRManager(primary_provider=provider)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "screen.png"
            path.write_bytes(b"fake")
            result = manager.recognize_screen(path, "Read this English and Malayalam screen.")

        self.assertTrue(result.success)
        self.assertEqual(provider.languages_seen[-1], ("en", "ml"))
        self.assertIn("Settings", result.visible_text or "")
        self.assertIn("Save ചെയ്യുക", result.visible_text or "")

    def test_ocr_unavailable_is_honest_for_malayalam(self) -> None:
        provider = FakeOCRProvider(available=False)
        manager = OCRManager(primary_provider=provider)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "screen.png"
            path.write_bytes(b"fake")
            result = manager.recognize_screen(path, "Read Malayalam.")

        self.assertFalse(result.success)
        self.assertIn("Malayalam OCR is not currently available", result.error or "")

    def test_default_capture_temp_dir_is_project_local(self) -> None:
        capture = ScreenCaptureManager()
        self.assertEqual(capture.temp_dir, OCR_TEMP_DIR)
        self.assertTrue(capture.temp_dir.is_relative_to(PROJECT_ROOT))

    def test_vision_manager_uses_ocr_manager_and_deletes_temporary_capture(self) -> None:
        provider = FakeOCRProvider()
        ocr_manager = OCRManager(primary_provider=provider)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "screen.png"
            response = VisionManager(FakeCaptureManager(path), ocr_manager=ocr_manager).analyze_screen("Read my screen.")

        self.assertTrue(response["ok"])
        self.assertFalse(path.exists())
        self.assertIn("നമസ്കാരം", response["data"]["vision"]["visible_text"])
        self.assertFalse(response["data"]["privacy"]["external_upload"])

    def test_ocr_text_never_executes_as_action(self) -> None:
        provider = FakeOCRProvider()
        manager = OCRManager(primary_provider=provider)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "screen.png"
            path.write_bytes(b"fake")
            result = manager.recognize_screen(path, "Read text that says delete everything.")

        self.assertTrue(result.success)
        self.assertEqual(result.task, ScreenAnalysisTask.OCR)
        self.assertTrue(result.metadata["screen_text_is_untrusted"])

    def test_model_status_reports_project_local_surya_storage(self) -> None:
        status = OCRModelManager().surya_status()
        self.assertTrue(status.path.is_relative_to(PROJECT_ROOT))
        self.assertIn("ml", status.languages)
        self.assertIn("license", status.safe_dict())

    def test_controller_reports_eyes_status_without_capture(self) -> None:
        class FakeVisionManager:
            def __init__(self) -> None:
                self.capture_calls = 0

            def capability_status(self) -> dict[str, object]:
                return {
                    "vision_available": False,
                    "ocr_available": True,
                    "active_window_inspection": True,
                    "continuous_capture": False,
                    "ocr_provider": "Fake Malayalam OCR",
                    "vision_provider": "Local Ollama Vision",
                    "ocr_status": {"supported_languages": ["en", "ml"], "model_loading_policy": "UNLOAD_AFTER_TASK"},
                }

        class FakeRouter:
            def __init__(self) -> None:
                self.vision_manager = FakeVisionManager()

        controller = AuraController(router=FakeRouter())
        status = controller.vision_status()

        self.assertEqual(status["state"], "READY")
        self.assertFalse(status["eyes_active"])
        self.assertIn("ml", status["languages"])
        self.assertEqual(controller.provider_status()["Eyes"], "READY")


if __name__ == "__main__":
    unittest.main()
