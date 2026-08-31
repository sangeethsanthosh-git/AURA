"""Primary local OCR provider for Malayalam and mixed-language screen text."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from backend.vision.ocr.base import OCRProvider, OCRRegion, OCRResult
from backend.vision.ocr.model_manager import OCRModelManager


class SuryaOCRProvider(OCRProvider):
    """Lazy Surya adapter.

    Surya is selected because the prior project research found explicit
    Malayalam (`ml`) recognition evidence. The adapter avoids importing Surya
    until OCR is requested so AURA starts with Eyes OFF and models unloaded.
    """

    provider_name = "Surya OCR"

    def __init__(self, model_manager: OCRModelManager | None = None, unload_after_task: bool = True) -> None:
        self.model_manager = model_manager or OCRModelManager()
        self.unload_after_task = unload_after_task
        self._runtime: dict[str, Any] | None = None

    def is_available(self) -> bool:
        return self.model_manager.surya_status().installed

    def supported_languages(self) -> tuple[str, ...]:
        return ("en", "ml", "mixed")

    def recognize(self, image_path: Path, languages: tuple[str, ...]) -> OCRResult:
        if not self.is_available():
            return OCRResult(
                False,
                self.provider_name,
                error="Malayalam OCR is not currently available because Surya OCR is not installed.",
                languages=languages,
                model="surya",
                metadata=self.model_manager.surya_status().safe_dict(),
            )

        started = time.perf_counter()
        self.model_manager.apply_environment()
        try:
            runtime = self._load_runtime()
            result = self._run_surya(runtime, image_path, languages)
            metadata = dict(result.metadata)
            metadata["load_policy"] = "UNLOAD_AFTER_TASK" if self.unload_after_task else "KEEP_WARM"
            metadata["ocr_inference_latency_seconds"] = round(time.perf_counter() - started, 3)
            return OCRResult(
                result.success,
                result.provider,
                result.text,
                result.languages,
                result.regions,
                result.confidence,
                result.model,
                result.error,
                metadata,
            )
        except Exception as exc:
            return OCRResult(False, self.provider_name, error=f"Surya OCR failed: {exc}", languages=languages, model="surya")
        finally:
            if self.unload_after_task:
                self.unload()

    def unload(self) -> None:
        self._runtime = None

    def _load_runtime(self) -> dict[str, Any]:
        if self._runtime is not None:
            return self._runtime

        try:
            from PIL import Image
            from surya.ocr import run_ocr
            from surya.model.detection.model import load_model as load_detection_model
            from surya.model.detection.processor import load_processor as load_detection_processor
            from surya.model.recognition.model import load_model as load_recognition_model
            from surya.model.recognition.processor import load_processor as load_recognition_processor

            self._runtime = {
                "api": "legacy_run_ocr",
                "image": Image,
                "run_ocr": run_ocr,
                "det_model": load_detection_model(),
                "det_processor": load_detection_processor(),
                "rec_model": load_recognition_model(),
                "rec_processor": load_recognition_processor(),
            }
            return self._runtime
        except Exception:
            from PIL import Image
            from surya.recognition import RecognitionPredictor
            from surya.detection import DetectionPredictor

            self._runtime = {
                "api": "predictors",
                "image": Image,
                "recognition": RecognitionPredictor(),
                "detection": DetectionPredictor(),
            }
            return self._runtime

    def _run_surya(self, runtime: dict[str, Any], image_path: Path, languages: tuple[str, ...]) -> OCRResult:
        image = runtime["image"].open(image_path)
        normalized_languages = tuple("en" if lang == "mixed" else lang for lang in languages) or ("en", "ml")
        if "ml" in languages and "ml" not in normalized_languages:
            normalized_languages = normalized_languages + ("ml",)

        if runtime["api"] == "legacy_run_ocr":
            predictions = runtime["run_ocr"](
                [image],
                [list(normalized_languages)],
                runtime["det_model"],
                runtime["det_processor"],
                runtime["rec_model"],
                runtime["rec_processor"],
            )
        else:
            predictions = runtime["recognition"]([image], [list(normalized_languages)], runtime["detection"])

        regions = self._normalize_predictions(predictions[0] if predictions else None)
        text = "\n".join(region.text for region in regions if region.text).strip()
        confidence_values = [region.confidence for region in regions if region.confidence is not None]
        confidence = round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else None
        return OCRResult(
            True,
            self.provider_name,
            text=text,
            languages=languages,
            regions=tuple(regions),
            confidence=confidence,
            model="surya",
        )

    @staticmethod
    def _normalize_predictions(prediction: Any) -> list[OCRRegion]:
        lines = getattr(prediction, "text_lines", None) or getattr(prediction, "lines", None) or []
        regions: list[OCRRegion] = []
        for line in lines:
            text = str(getattr(line, "text", "") or "").strip()
            if not text:
                continue
            bbox_raw = getattr(line, "bbox", None) or getattr(line, "polygon", None)
            bbox = tuple(int(value) for value in bbox_raw[:4]) if bbox_raw and len(bbox_raw) >= 4 else None
            confidence = getattr(line, "confidence", None)
            regions.append(OCRRegion(text=text, confidence=confidence, bbox=bbox))
        return regions

