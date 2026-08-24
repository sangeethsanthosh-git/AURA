"""Project-local OCR model and cache locations.

This module intentionally avoids importing OCR libraries. It can be used before
optional OCR dependencies are installed to prepare local storage and environment
overrides for model download/cache behavior.
"""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

OCR_MODEL_ROOT = PROJECT_ROOT / "models" / "ocr"
OCR_PRIMARY_DIR = OCR_MODEL_ROOT / "primary"
OCR_MALAYALAM_DIR = OCR_MODEL_ROOT / "malayalam"
OCR_FALLBACK_DIR = OCR_MODEL_ROOT / "fallback"
OCR_DETECTION_DIR = OCR_MODEL_ROOT / "detection"
OCR_RECOGNITION_DIR = OCR_MODEL_ROOT / "recognition"

OCR_DATA_ROOT = PROJECT_ROOT / "data" / "ocr"
OCR_CACHE_DIR = OCR_DATA_ROOT / "cache"
OCR_TEMP_DIR = OCR_DATA_ROOT / "temporary"

_ALL_OCR_DIRS = (
    OCR_PRIMARY_DIR,
    OCR_MALAYALAM_DIR,
    OCR_FALLBACK_DIR,
    OCR_DETECTION_DIR,
    OCR_RECOGNITION_DIR,
    OCR_CACHE_DIR,
    OCR_TEMP_DIR,
)


def ensure_ocr_directories() -> tuple[Path, ...]:
    """Create the OCR directory layout under the project root."""

    for path in _ALL_OCR_DIRS:
        path.mkdir(parents=True, exist_ok=True)
    return _ALL_OCR_DIRS


def ocr_environment() -> dict[str, str]:
    """Return environment overrides that keep OCR artifacts project-local.

    The caller should merge this into the process environment before importing
    OCR libraries that may auto-download models.
    """

    cache_root = OCR_CACHE_DIR
    return {
        "AURA_OCR_MODEL_DIR": os.fspath(OCR_MODEL_ROOT),
        "AURA_OCR_CACHE_DIR": os.fspath(cache_root),
        "AURA_OCR_TEMP_DIR": os.fspath(OCR_TEMP_DIR),
        "EASYOCR_MODULE_PATH": os.fspath(OCR_MODEL_ROOT / "easyocr"),
        "HF_HOME": os.fspath(cache_root / "huggingface"),
        "HF_HUB_CACHE": os.fspath(cache_root / "huggingface" / "hub"),
        "TRANSFORMERS_CACHE": os.fspath(cache_root / "huggingface" / "transformers"),
        "XDG_CACHE_HOME": os.fspath(cache_root / "xdg"),
        "TMP": os.fspath(OCR_TEMP_DIR),
        "TEMP": os.fspath(OCR_TEMP_DIR),
    }
