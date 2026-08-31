"""Response metadata formatter for router outputs."""

from __future__ import annotations

import logging
import time
from typing import Any

from backend.router.intent_classifier import IntentResult
from backend.router.provider_selector import ProviderPlan

LOGGER = logging.getLogger(__name__)


class ResponseFormatter:
    """Attaches display metadata without changing assistant message text."""

    def format(
        self,
        response: dict[str, Any],
        classification: IntentResult,
        plan: ProviderPlan,
        started_at: float,
        success_provider: str | None = None,
    ) -> dict[str, Any]:
        execution = round(time.perf_counter() - started_at, 2)
        provider = success_provider or plan.provider
        data = response.setdefault("data", {})
        llm_used, llm_provider = self._llm_metadata(response)
        model = self._model_for(response) if llm_used else "None"
        execution_source = response.get("execution_source") or self._execution_source_for(response, plan)
        response["route"] = {
            "intent": classification.intent.value,
            "confidence": classification.confidence,
            "language": self._language_for(response),
            "provider": provider,
            "model": model,
            "source": execution_source,
            "execution_source": execution_source,
            "llm_provider": llm_provider,
            "llm_model": model if llm_provider else None,
            "llm_used": llm_used,
            "integrity_check": response.get("integrity_check", "NOT_APPLICABLE"),
            "api_used": execution_source,
            "fallback": self._fallback_for(provider, plan),
            "execution_time_seconds": execution,
            "success": bool(response.get("ok")),
        }
        data.setdefault("model", model)
        data.setdefault("source", plan.source)
        self._log(response)
        return response

    @staticmethod
    def _model_for(response: dict[str, Any]) -> str:
        return str(response.get("data", {}).get("model") or "Unknown")

    @staticmethod
    def _llm_metadata(response: dict[str, Any]) -> tuple[bool, str | None]:
        explicit = response.get("llm_used")
        explicit_provider = response.get("llm_provider")
        if explicit is not None:
            return bool(explicit), str(explicit_provider) if explicit_provider else None

        if not response.get("ok"):
            return False, None

        provider = str(response.get("provider", "")).lower()
        names = {
            "ollama": "Ollama",
            "groq": "Groq",
            "huggingface": "Hugging Face",
            "nvidia": "NVIDIA",
        }
        if provider in names:
            return True, names[provider]
        return False, None

    @staticmethod
    def _execution_source_for(response: dict[str, Any], plan: ProviderPlan) -> str:
        provider = str(response.get("provider", "")).lower()
        action = str(response.get("action", "")).lower()
        if provider == "memory":
            if action in {"remember", "recall", "summary", "search", "forget"}:
                return "Long-Term Memory"
            if action == "daily_recall":
                return "Daily Memory"
            if action in {"conversation_recall", "clear_session"}:
                return "Session Memory"
            if action == "clear_all":
                return "Multiple Memory Layers"
            return "Local Memory"
        if provider == "knowledge":
            if action in {"temporary_analysis", "temporary_query", "clear_temporary", "file_operation"}:
                return "Temporary Document Context"
            return "Local Knowledge Base"
        sources = {
            "ollama": "Local AI",
            "groq": "Groq API",
            "huggingface": "Hugging Face Router",
            "nvidia": "NVIDIA NIM API",
            "wikipedia": "Wikipedia API",
            "web": "Web Intelligence",
            "weather": "Live Weather API",
            "maps": "OpenStreetMap Nominatim",
            "location": "Location Service",
            "math": "Python Math Engine",
            "actions": "AURA HANDS",
            "agent": "AURA Agent Loop",
            "vision": "AURA EYES",
        }
        return sources.get(provider, plan.source)

    @staticmethod
    def _fallback_for(provider: str, plan: ProviderPlan) -> str:
        if provider != plan.provider and provider in plan.fallbacks:
            return provider
        return "None"

    @staticmethod
    def _language_for(response: dict[str, Any]) -> str:
        language = response.get("data", {}).get("language")
        return {"en": "English", "ml": "Malayalam"}.get(language, "English")

    @staticmethod
    def _log(response: dict[str, Any]) -> None:
        route = response["route"]
        LOGGER.info(
            "\n==============================\n"
            "Intent\n%s\n\nConfidence\n%s\n\nExecution Source\n%s\n\nLLM Used\n%s\n\nLLM Provider\n%s\n\n"
            "Integrity Check\n%s\n\nProvider\n%s\n\nFallback\n%s\n\nExecution\n%.2f sec\n"
            "==============================",
            route["intent"],
            route["confidence"],
            route["execution_source"],
            route["llm_used"],
            route["llm_provider"],
            route["integrity_check"],
            route["provider"],
            route["fallback"],
            route["execution_time_seconds"],
        )
