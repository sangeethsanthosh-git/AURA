"""Production-style staged Smart Router for AURA."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from backend.router.fallback_manager import FallbackManager
from backend.router.intent_classifier import Intent, IntentClassifier, IntentResult
from backend.router.knowledge_handler import KnowledgeHandler
from backend.knowledge.knowledge_manager import KnowledgeManager
from backend.router.knowledge_base_handler import KnowledgeBaseHandler
from backend.router.math_engine import MathEngine
from backend.memory.memory_manager import MemoryManager
from backend.router.programming_handler import ProgrammingHandler
from backend.router.provider_selector import ProviderSelector
from backend.router.reasoning_handler import ReasoningHandler
from backend.router.response_formatter import ResponseFormatter
from backend.router.service_manager import ServiceManager
from backend.router.tool_integrity import deterministic_tool_result, safe_math_response, validate_math_response
from backend.router.translation_handler import TranslationHandler
from backend.router.weather_handler import WeatherHandler
from backend.utils.responses import error_response

LOGGER = logging.getLogger(__name__)


class SmartRouter:
    """Runs requests through memory, classification, provider, fallback, format."""

    def __init__(
        self,
        service_manager: ServiceManager | None = None,
        classifier: IntentClassifier | None = None,
        memory_manager: MemoryManager | None = None,
        knowledge_manager: KnowledgeManager | None = None,
    ) -> None:
        self.service_manager = service_manager or ServiceManager()
        self.classifier = classifier or IntentClassifier()
        self.memory_manager = memory_manager or MemoryManager()
        self.knowledge_manager = knowledge_manager or KnowledgeManager()
        self.provider_selector = ProviderSelector()
        self.fallbacks = FallbackManager()
        self.formatter = ResponseFormatter()
        self.math_engine = MathEngine()
        self.handlers: dict[Intent, Callable[[IntentResult, str], dict[str, Any]]] = {
            Intent.MEMORY: self._handle_memory,
            Intent.MATHEMATICS: self._handle_math,
            Intent.REASONING: lambda _, prompt: self._reasoning().handle(prompt),
            Intent.PROGRAMMING: lambda _, prompt: self._programming().handle(prompt),
            Intent.TRANSLATION: lambda _, prompt: self._translation().handle(prompt),
            Intent.GENERAL_KNOWLEDGE: lambda classification, prompt: self._knowledge().handle(classification, prompt),
            Intent.WEATHER: lambda classification, _: self._weather().handle(classification),
            Intent.LOCATION: lambda classification, _: self.service_manager.ask("maps", classification.query),
            Intent.MAPS: lambda classification, _: self.service_manager.ask("maps", classification.query),
            Intent.CONVERSATION: lambda _, prompt: self.service_manager.ask("ollama", prompt),
            Intent.DOCUMENTS: lambda _, prompt: self._knowledge_base().handle_knowledge(prompt),
            Intent.RAG: lambda _, prompt: self._knowledge_base().handle_knowledge(prompt),
            Intent.FILE_OPERATIONS: lambda _, prompt: self._knowledge_base().handle_file_operation(prompt),
            Intent.FINANCE: lambda *_: error_response("finance", "finance", "Finance service is not installed."),
            Intent.SYSTEM_COMMANDS: lambda *_: error_response("system", "system_commands", "System command handling is available in the CLI."),
        }

    def ask(self, user_input: str) -> dict[str, Any]:
        started_at = time.perf_counter()
        try:
            classification = self._detect_memory_first(user_input)
            plan = self.provider_selector.select(classification.intent)
            handler = self.handlers.get(classification.intent, self._unknown)
            response = handler(classification, user_input)
            if classification.intent != Intent.MEMORY:
                self.memory_manager.observe_interaction(user_input, response)
            success_provider = self._success_provider(response, plan.provider)
            return self.formatter.format(response, classification, plan, started_at, success_provider)
        except Exception as exc:
            LOGGER.exception("SmartRouter failed.")
            classification = IntentResult(Intent.UNKNOWN, 0.0, user_input, "Ollama", "SmartRouter exception fallback.")
            plan = self.provider_selector.select(Intent.UNKNOWN)
            response = error_response("smart_router", "ask", "Sorry, something went wrong.", details=repr(exc))
            return self.formatter.format(response, classification, plan, started_at)

    def _detect_memory_first(self, user_input: str) -> IntentResult:
        memory_decision = self.memory_manager.analyze(user_input)
        if memory_decision.requires_memory:
            LOGGER.info("Stage 1 Memory Detection: operation=%s confidence=%s", memory_decision.operation, memory_decision.confidence)
            return IntentResult(
                Intent.MEMORY,
                memory_decision.confidence,
                user_input,
                "MemoryManager",
                "MemoryManager detected a personal memory operation.",
            )

        classification = self.classifier.classify(user_input)
        LOGGER.info("Stage 2 Intent Classification: intent=%s confidence=%s", classification.intent, classification.confidence)
        return classification

    def _handle_memory(self, _: IntentResult, prompt: str) -> dict[str, Any]:
        return self.memory_manager.handle(prompt)

    def _handle_math(self, _: IntentResult, prompt: str) -> dict[str, Any]:
        local = self.math_engine.solve(prompt)
        if not local.get("ok"):
            return local

        data = local.setdefault("data", {})
        data["tool_result"] = deterministic_tool_result(
            "python_math_engine",
            "local",
            {
                "expression": data.get("expression"),
                "result": data.get("result"),
            },
        )
        local["execution_source"] = "Python Math Engine"
        local["llm_used"] = False
        local["llm_provider"] = None
        local["integrity_check"] = "PASSED"

        if not self._needs_math_explanation(prompt):
            return local

        llm_prompt = self._math_explanation_prompt(data, prompt)
        explanation = self.service_manager.ask("ollama", llm_prompt)
        local["llm_used"] = bool(explanation.get("ok"))
        local["llm_provider"] = "Ollama" if explanation.get("ok") else None
        if explanation.get("ok"):
            final_text = str(explanation.get("message") or explanation.get("data", {}).get("content") or "")
            if validate_math_response(data.get("result"), final_text):
                local["message"] = final_text
            else:
                local["message"] = safe_math_response(str(data.get("expression")), data.get("result"))
                local["integrity_check"] = "REPLACED_LLM_OUTPUT"
        return local

    @staticmethod
    def _needs_math_explanation(prompt: str) -> bool:
        lowered = prompt.lower()
        return any(word in lowered for word in ("explain", "how", "steps", "show work", "why"))

    @staticmethod
    def _math_explanation_prompt(data: dict[str, Any], original_prompt: str) -> str:
        return (
            "The following calculation was executed by a trusted deterministic math engine.\n\n"
            f"Expression:\n{data.get('expression')}\n\n"
            f"Verified Result:\n{data.get('result')}\n\n"
            "Explain the calculation for the user. Do not recalculate, replace, "
            "or alter the verified result.\n\n"
            f"User request:\n{original_prompt}"
        )

    def _unknown(self, _: IntentResult, prompt: str) -> dict[str, Any]:
        return self.service_manager.ask("ollama", prompt)

    def _programming(self) -> ProgrammingHandler:
        return ProgrammingHandler(self.service_manager, self.fallbacks)

    def _reasoning(self) -> ReasoningHandler:
        return ReasoningHandler(self.service_manager, self.fallbacks)

    def _translation(self) -> TranslationHandler:
        return TranslationHandler(self.service_manager, self.fallbacks)

    def _knowledge(self) -> KnowledgeHandler:
        return KnowledgeHandler(self.service_manager, self.fallbacks)

    def _knowledge_base(self) -> KnowledgeBaseHandler:
        return KnowledgeBaseHandler(self.knowledge_manager)

    def _weather(self) -> WeatherHandler:
        return WeatherHandler(self.service_manager)

    @staticmethod
    def _success_provider(response: dict[str, Any], default: str) -> str:
        provider = str(response.get("provider", default))
        names = {
            "groq": "Groq",
            "ollama": "Ollama",
            "huggingface": "Hugging Face",
            "wikipedia": "Wikipedia",
            "weather": "Open-Meteo",
            "maps": "OpenStreetMap",
            "math": "Local Math Engine",
            "memory": "MemoryManager",
            "knowledge": "Local Knowledge",
        }
        return names.get(provider, default)


def build_smart_router(service_manager: ServiceManager | None = None) -> SmartRouter:
    """Factory used by CLI and future desktop entry points."""
    return SmartRouter(service_manager=service_manager)
