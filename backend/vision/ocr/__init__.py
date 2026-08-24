"""Project-local OCR scaffolding for AURA Eyes."""

from .paths import (
    OCR_CACHE_DIR,
    OCR_DETECTION_DIR,
    OCR_FALLBACK_DIR,
    OCR_MALAYALAM_DIR,
    OCR_MODEL_ROOT,
    OCR_PRIMARY_DIR,
    OCR_RECOGNITION_DIR,
    OCR_TEMP_DIR,
    ensure_ocr_directories,
    ocr_environment,
)

__all__ = [
    "OCR_CACHE_DIR",
    "OCR_DETECTION_DIR",
    "OCR_FALLBACK_DIR",
    "OCR_MALAYALAM_DIR",
    "OCR_MODEL_ROOT",
    "OCR_PRIMARY_DIR",
    "OCR_RECOGNITION_DIR",
    "OCR_TEMP_DIR",
    "ensure_ocr_directories",
    "ocr_environment",
]
