import unittest
from pathlib import Path

from backend.vision.ocr.paths import (
    OCR_CACHE_DIR,
    OCR_DETECTION_DIR,
    OCR_FALLBACK_DIR,
    OCR_MALAYALAM_DIR,
    OCR_MODEL_ROOT,
    OCR_PRIMARY_DIR,
    OCR_RECOGNITION_DIR,
    OCR_TEMP_DIR,
    PROJECT_ROOT,
    ensure_ocr_directories,
    ocr_environment,
)


class OcrStorageTest(unittest.TestCase):
    def test_ocr_directories_are_project_local(self):
        paths = ensure_ocr_directories()

        expected = {
            OCR_MODEL_ROOT / "primary",
            OCR_MODEL_ROOT / "malayalam",
            OCR_MODEL_ROOT / "fallback",
            OCR_MODEL_ROOT / "detection",
            OCR_MODEL_ROOT / "recognition",
            PROJECT_ROOT / "data" / "ocr" / "cache",
            PROJECT_ROOT / "data" / "ocr" / "temporary",
        }

        self.assertEqual(set(paths), expected)
        for path in expected:
            self.assertTrue(path.exists(), path)
            self.assertTrue(path.is_dir(), path)
            self.assertTrue(path.is_relative_to(PROJECT_ROOT), path)

    def test_ocr_environment_redirects_caches_inside_project(self):
        env = ocr_environment()

        for key in (
            "AURA_OCR_MODEL_DIR",
            "AURA_OCR_CACHE_DIR",
            "AURA_OCR_TEMP_DIR",
            "EASYOCR_MODULE_PATH",
            "HF_HOME",
            "HF_HUB_CACHE",
            "TRANSFORMERS_CACHE",
            "XDG_CACHE_HOME",
            "TMP",
            "TEMP",
        ):
            self.assertIn(key, env)
            self.assertTrue(Path(env[key]).is_relative_to(PROJECT_ROOT), key)

        self.assertEqual(Path(env["AURA_OCR_CACHE_DIR"]), OCR_CACHE_DIR)
        self.assertEqual(Path(env["AURA_OCR_TEMP_DIR"]), OCR_TEMP_DIR)


if __name__ == "__main__":
    unittest.main()
