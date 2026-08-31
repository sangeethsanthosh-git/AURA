"""OCR manager for AURA Eyes V1."""

from __future__ import annotations

import re
import time
from pathlib import Path

from backend.vision.models import ScreenAnalysisTask, VisibleElement, VisionResult
from backend.vision.ocr.base import OCRProvider, OCRResult
from backend.vision.ocr.model_manager import OCRModelManager
from backend.vision.ocr.preprocessing import OcrPreprocessor
from backend.vision.ocr.providers.primary import SuryaOCRProvider


_MALAYALAM_RANGE = re.compile(r"[\u0D00-\u0D7F]")


class OCRManager:
    """Selects OCR providers, runs preprocessing, and normalizes results."""

    def __init__(
        self,
        primary_provider: OCRProvider | None = None,
        model_manager: OCRModelManager | None = None,
        preprocessor: OcrPreprocessor | None = None,
        unload_after_task: bool = True,
    ) -> None:
        self.model_manager = model_manager or OCRModelManager()
        self.primary_provider = primary_provider or SuryaOCRProvider(self.model_manager, unload_after_task=unload_after_task)
        self.preprocessor = preprocessor or OcrPreprocessor()
        self.unload_after_task = unload_after_task
        self.last_result: OCRResult | None = None

    def is_available(self) -> bool:
        return self.primary_provider.is_available()

    def supported_languages(self) -> tuple[str, ...]:
        return self.primary_provider.supported_languages()

    def status(self) -> dict[str, object]:
        return {
            "state": "READY" if self.is_available() else "UNAVAILABLE",
            "provider": self.primary_provider.provider_name,
            "available": self.is_available(),
            "supported_languages": list(self.supported_languages()),
            "model_loading_policy": "UNLOAD_AFTER_TASK" if self.unload_after_task else "KEEP_WARM",
            "models": self.model_manager.status(),
        }

    def recognize_screen(self, image_path: Path, prompt: str = "") -> VisionResult:
        started = time.perf_counter()
        languages = self.route_languages(prompt)
        prepared = self.preprocessor.prepare(image_path)
        result = self.primary_provider.recognize(prepared, languages)
        self.last_result = result
        metadata = result.safe_dict()
        metadata["ocr_total_latency_seconds"] = round(time.perf_counter() - started, 3)
        metadata["screen_text_is_untrusted"] = True
        if not result.success:
            return VisionResult(
                False,
                ScreenAnalysisTask.OCR,
                "",
                result.provider,
                model=result.model,
                error=result.error or "AURA Eyes could not read the screen.",
                metadata=metadata,
            )

        description = "No visible text detected." if not result.text else f"Visible text detected: {' '.join(result.text.split())[:800]}"
        return VisionResult(
            True,
            ScreenAnalysisTask.OCR,
            description,
            result.provider,
            model=result.model,
            visible_text=result.text,
            elements=[
                VisibleElement("text", text=region.text, bounding_box=region.bbox, confidence=region.confidence)
                for region in result.regions
            ],
            confidence=result.confidence,
            metadata=metadata,
        )

    @staticmethod
    def route_languages(prompt: str) -> tuple[str, ...]:
        lowered = prompt.lower()
        requested_malayalam = "malayalam" in lowered or "ml" in lowered or bool(_MALAYALAM_RANGE.search(prompt))
        requested_english = "english" in lowered or "latin" in lowered or "manglish" in lowered
        if requested_malayalam and requested_english:
            return ("en", "ml")
        if requested_malayalam:
            return ("ml", "en")
        return ("en", "ml")

