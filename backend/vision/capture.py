"""One-shot screen capture with temporary file lifecycle."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from uuid import uuid4

from backend.vision.models import CaptureRegionType, ScreenCaptureResult
from backend.vision.ocr.paths import OCR_TEMP_DIR, ensure_ocr_directories

LOGGER = logging.getLogger(__name__)


class ScreenCaptureManager:
    """Captures the current screen only when explicitly requested."""

    def __init__(self, temp_dir: Path | None = None, max_dimension: int = 1600) -> None:
        ensure_ocr_directories()
        self.temp_dir = temp_dir or OCR_TEMP_DIR
        self.max_dimension = max_dimension

    def capture_screen(
        self,
        monitor: int = 0,
        region_type: CaptureRegionType = CaptureRegionType.FULL_SCREEN,
        region: tuple[int, int, int, int] | None = None,
    ) -> ScreenCaptureResult:
        started = time.perf_counter()
        try:
            from PIL import ImageGrab
        except ImportError:
            return ScreenCaptureResult(False, error="Pillow is not installed; screen capture is unavailable.")

        try:
            bbox = self._bbox_for(region_type, region)
            image = ImageGrab.grab(bbox=bbox, all_screens=False)
            width, height = image.size
            image = self._resize_if_needed(image)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            path = self.temp_dir / f"screen_{uuid4().hex}.png"
            image.save(path, "PNG")
            LOGGER.info("Screen capture successful width=%s height=%s temp=%s", width, height, path)
            return ScreenCaptureResult(
                True,
                width=width,
                height=height,
                monitor=monitor,
                temporary_path=path,
                metadata={
                    "capture_latency_seconds": round(time.perf_counter() - started, 3),
                    "processed_width": image.size[0],
                    "processed_height": image.size[1],
                    "region_type": region_type.value,
                    "region": region,
                },
            )
        except Exception as exc:
            LOGGER.exception("Screen capture failed.")
            return ScreenCaptureResult(False, error=f"Screen capture failed: {exc}")

    def cleanup(self, capture: ScreenCaptureResult) -> bool:
        path = capture.temporary_path
        if not path:
            return False
        try:
            if path.exists():
                path.unlink()
                LOGGER.info("Temporary screen capture deleted: %s", path)
                return True
        except OSError:
            LOGGER.exception("Temporary screen capture cleanup failed.")
        return False

    def _resize_if_needed(self, image):
        width, height = image.size
        largest = max(width, height)
        if largest <= self.max_dimension:
            return image
        scale = self.max_dimension / largest
        size = (max(1, int(width * scale)), max(1, int(height * scale)))
        return image.resize(size)

    @staticmethod
    def _bbox_for(region_type: CaptureRegionType, region: tuple[int, int, int, int] | None):
        if region_type == CaptureRegionType.REGION and region:
            x, y, width, height = region
            return (x, y, x + width, y + height)
        if region_type == CaptureRegionType.ACTIVE_WINDOW:
            # Active-window capture can be added with a Windows foreground-window API.
            # Falling back to full screen keeps V1 safe and predictable.
            return None
        return None
