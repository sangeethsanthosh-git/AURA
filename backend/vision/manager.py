"""Screen capture plus vision analysis orchestration."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from backend.context.models import ContextSourceType
from backend.context.temporary import TemporaryContextStore
from backend.utils.responses import error_response, success_response
from backend.vision.capture import ScreenCaptureManager
from backend.vision.models import CaptureRegionType, ScreenAnalysisTask, ScreenCaptureResult, VisionResult, VisualContext
from backend.vision.providers import LocalOllamaVisionProvider, OptionalTesseractOcrProvider, VisionProvider
from backend.vision.window_inspector import ActiveWindowInspector

LOGGER = logging.getLogger(__name__)


class VisionManager:
    def __init__(
        self,
        capture_manager: ScreenCaptureManager | None = None,
        provider: VisionProvider | None = None,
        ocr_provider: VisionProvider | None = None,
        temporary_context: TemporaryContextStore | None = None,
        visual_context_ttl_seconds: int = 45,
        window_inspector: ActiveWindowInspector | None = None,
    ) -> None:
        self.capture_manager = capture_manager or ScreenCaptureManager()
        self.provider = provider or LocalOllamaVisionProvider()
        self.ocr_provider = ocr_provider or OptionalTesseractOcrProvider()
        self.temporary_context = temporary_context
        self.visual_context_ttl_seconds = visual_context_ttl_seconds
        self.capture_count = 0
        self.inference_count = 0
        self.last_visual_context: VisualContext | None = None
        self.window_inspector = window_inspector or ActiveWindowInspector()

    def analyze_screen(
        self,
        prompt: str,
        task: ScreenAnalysisTask | None = None,
        *,
        region_type: CaptureRegionType = CaptureRegionType.FULL_SCREEN,
        region: tuple[int, int, int, int] | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        selected_task = task or self.task_from_prompt(prompt)
        LOGGER.info("Vision requested task=%s region_type=%s", selected_task.value, region_type.value)
        if selected_task in {ScreenAnalysisTask.APPLICATION_IDENTIFICATION, ScreenAnalysisTask.WINDOW_IDENTIFICATION}:
            active = self.describe_active_window()
            if active.get("ok"):
                return active
            LOGGER.info("Active-window inspection unavailable; falling back to screen analysis.")
        try:
            capture = self.capture_manager.capture_screen(region_type=region_type, region=region)
        except TypeError:
            capture = self.capture_manager.capture_screen()
        self.capture_count += 1
        cleanup_done = False
        if not capture.success:
            return error_response("vision", selected_task.value, capture.error or "Screen capture failed.")
        try:
            if not capture.temporary_path:
                return error_response("vision", selected_task.value, "Screen capture did not produce an analyzable image.")
            result = self._analyze_capture(capture.temporary_path, selected_task, prompt)
            if result.success:
                self.inference_count += 1
            visual_context = self._visual_context(result, selected_task, capture)
            self.last_visual_context = visual_context
            self._store_temporary_context(visual_context)
            data = {
                "capture": self._capture_metadata(capture),
                "vision": result.safe_dict(),
                "visual_context": visual_context.safe_dict(),
                "privacy": {
                    "temporary_capture": True,
                    "screenshot_history": False,
                    "screen_content_added_to_memory": False,
                    "external_upload": False,
                    "screen_content_logged": False,
                },
                "analysis_duration_seconds": round(time.perf_counter() - started, 3),
                "benchmarks": self._benchmark_data(started, capture, result),
            }
            if result.success:
                response = success_response("vision", selected_task.value, data, result.description)
            else:
                response = error_response("vision", selected_task.value, result.error or result.description, details=data)
            response["execution_source"] = result.provider
            response["llm_used"] = result.success
            response["llm_provider"] = result.provider if result.success else None
            if result.model:
                response.setdefault("data", data)["model"] = result.model
            return response
        finally:
            cleanup_done = self.capture_manager.cleanup(capture)
            LOGGER.info("Screen analysis cleanup_done=%s", cleanup_done)

    def capability_status(self) -> dict[str, Any]:
        return {
            "screen_capture": "available when Pillow/ImageGrab can access the desktop",
            "vision_provider": self.provider.provider_name,
            "vision_available": self.provider.is_available(),
            "ocr_provider": self.ocr_provider.provider_name,
            "ocr_available": self.ocr_provider.is_available(),
            "continuous_capture": False,
            "capture_count": self.capture_count,
            "vision_inference_count": self.inference_count,
            "visual_context_ttl_seconds": self.visual_context_ttl_seconds,
            "active_window_inspection": True,
        }

    def describe_active_window(self) -> dict[str, Any]:
        started = time.perf_counter()
        active = self.window_inspector.get_active_window()
        if not active.success:
            return error_response("vision", ScreenAnalysisTask.APPLICATION_IDENTIFICATION.value, active.error or "Active window inspection failed.")
        now = datetime.now(timezone.utc)
        context = VisualContext(
            screen_id=uuid4().hex,
            created_at=now,
            expires_at=now + timedelta(seconds=self.visual_context_ttl_seconds),
            task=ScreenAnalysisTask.APPLICATION_IDENTIFICATION,
            application=active.application,
            window_title=active.title,
            description=f"Active application: {active.application or 'Unknown'}. Window title: {active.title or 'Unknown'}.",
            confidence=0.85 if active.application else 0.5,
            source="Windows foreground window",
            metadata=active.safe_dict(),
        )
        self.last_visual_context = context
        self._store_temporary_context(context)
        message = f"The active application appears to be {active.application or 'unknown'}."
        if active.title:
            message += f" Window title: {active.title}."
        return success_response(
            "vision",
            ScreenAnalysisTask.APPLICATION_IDENTIFICATION.value,
            {
                "active_window": active.safe_dict(),
                "visual_context": context.safe_dict(),
                "analysis_duration_seconds": round(time.perf_counter() - started, 3),
                "privacy": {
                    "temporary_capture": False,
                    "screenshot_history": False,
                    "screen_content_added_to_memory": False,
                    "external_upload": False,
                    "screen_content_logged": False,
                },
            },
            message,
        )

    @staticmethod
    def task_from_prompt(prompt: str) -> ScreenAnalysisTask:
        lowered = prompt.lower()
        if any(term in lowered for term in ("error", "exception", "traceback", "failed")):
            return ScreenAnalysisTask.ERROR_UNDERSTANDING
        if any(term in lowered for term in ("where is", "locate", "find the")):
            return ScreenAnalysisTask.TARGET_LOCATION
        if any(term in lowered for term in ("read", "text", "says", "shown here")):
            return ScreenAnalysisTask.OCR
        if lowered.startswith("did ") or "verify" in lowered:
            return ScreenAnalysisTask.ACTION_VERIFICATION
        if any(term in lowered for term in ("button", "field", "menu", "ui element")):
            return ScreenAnalysisTask.UI_ELEMENT_DETECTION
        if any(term in lowered for term in ("application", "app", "window")):
            return ScreenAnalysisTask.APPLICATION_IDENTIFICATION
        return ScreenAnalysisTask.SCREEN_DESCRIPTION

    @staticmethod
    def _capture_metadata(capture) -> dict[str, Any]:
        data = capture.safe_dict()
        data["temporary_path"] = None
        return data

    def _analyze_capture(self, image_path, selected_task: ScreenAnalysisTask, prompt: str) -> VisionResult:
        if selected_task in {ScreenAnalysisTask.OCR, ScreenAnalysisTask.TEXT_RECOGNITION}:
            ocr_result = self.ocr_provider.detect_text(image_path)
            if ocr_result.success or not self.provider.is_available():
                return ocr_result
        if selected_task in {ScreenAnalysisTask.UI_ELEMENT_DETECTION, ScreenAnalysisTask.UI_ELEMENT_DISCOVERY}:
            return self.provider.detect_elements(image_path, prompt)
        return self.provider.analyze(image_path, selected_task, prompt)

    def _visual_context(self, result: VisionResult, task: ScreenAnalysisTask, capture: ScreenCaptureResult) -> VisualContext:
        now = datetime.now(timezone.utc)
        text = result.visible_text if result.visible_text is not None else result.description if result.success else None
        sensitive = self._looks_sensitive(text or "")
        return VisualContext(
            screen_id=uuid4().hex,
            created_at=now,
            expires_at=now + timedelta(seconds=self.visual_context_ttl_seconds),
            task=task,
            application=self._application_from_text(result.description),
            window_title=None,
            visible_text=None if sensitive else text,
            description=result.description,
            elements=result.elements,
            confidence=result.confidence,
            source=result.provider,
            sensitive=sensitive,
            metadata={
                "capture_width": capture.width,
                "capture_height": capture.height,
                "provider_model": result.model,
            },
        )

    def _store_temporary_context(self, context: VisualContext) -> None:
        if self.temporary_context is None:
            return
        summary = f"Visual context task={context.task.value} source={context.source}"
        if context.application:
            summary += f" application={context.application}"
        if context.visible_text and not context.sensitive:
            summary += f" text={context.visible_text[:400]}"
        self.temporary_context.add(
            ContextSourceType.SYSTEM,
            summary,
            label="recent visual context",
            ttl_seconds=self.visual_context_ttl_seconds,
            metadata={"screen_id": context.screen_id, "sensitive": context.sensitive},
        )

    @staticmethod
    def _benchmark_data(started: float, capture: ScreenCaptureResult, result: VisionResult) -> dict[str, Any]:
        return {
            "screenshot_latency_seconds": capture.metadata.get("capture_latency_seconds"),
            "analysis_latency_seconds": round(time.perf_counter() - started, 3),
            "image_width": capture.metadata.get("processed_width", capture.width),
            "image_height": capture.metadata.get("processed_height", capture.height),
            "vision_provider": result.provider,
            "model": result.model,
            "model_size": "unknown",
            "ram_usage": "not_measured",
            "vram_usage": "not_measured",
        }

    @staticmethod
    def _looks_sensitive(text: str) -> bool:
        lowered = text.lower()
        return any(term in lowered for term in ("password", "otp", "one-time code", "credit card", "bank", "login", "authentication"))

    @staticmethod
    def _application_from_text(text: str) -> str | None:
        lowered = text.lower()
        for name in ("calculator", "chrome", "spotify", "notepad", "visual studio code", "edge"):
            if name in lowered:
                return " ".join(part.capitalize() for part in name.split())
        return None
