"""Production-style staged Smart Router for AURA."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from backend.context import ContextBuilder, TemporaryContextStore, collect_context_measurements
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
from backend.actions.manager import ActionManager
from backend.agent.controller import TaskController
from backend.vision.manager import VisionManager
from backend.web.manager import WebIntelligenceManager

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
        self.temporary_context = TemporaryContextStore()
        self.vision_manager = VisionManager(temporary_context=self.temporary_context)
        self.action_manager = ActionManager(verifier=None)
        self.action_manager.verifier.vision_manager = self.vision_manager
        self.task_controller = TaskController(self.action_manager)
        self.web_manager = WebIntelligenceManager(self.service_manager)
        self.web_manager.temporary_context = self.temporary_context
        self.task_controller.temporary_context = self.temporary_context
        self.context_builder = ContextBuilder(self.memory_manager, self.knowledge_manager, temporary_store=self.temporary_context)
        self.handlers: dict[Intent, Callable[[IntentResult, str], dict[str, Any]]] = {
            Intent.MEMORY: self._handle_memory,
            Intent.MATHEMATICS: self._handle_math,
            Intent.REASONING: lambda _, prompt: self._reasoning().handle(prompt),
            Intent.PROGRAMMING: lambda _, prompt: self._programming().handle(prompt),
            Intent.TRANSLATION: lambda _, prompt: self._translation().handle(prompt),
            Intent.GENERAL_KNOWLEDGE: lambda classification, prompt: self._knowledge().handle(classification, prompt),
            Intent.WEB_INTELLIGENCE: lambda _, prompt: self.web_manager.answer(prompt),
            Intent.WEATHER: lambda classification, _: self._weather().handle(classification),
            Intent.LOCATION: lambda classification, _: self.service_manager.ask("maps", classification.query),
            Intent.MAPS: lambda classification, _: self.service_manager.ask("maps", classification.query),
            Intent.CONVERSATION: lambda _, prompt: self.service_manager.ask("ollama", prompt),
            Intent.DOCUMENTS: lambda _, prompt: self._knowledge_base().handle_knowledge(prompt),
            Intent.RAG: lambda _, prompt: self._knowledge_base().handle_knowledge(prompt),
            Intent.FILE_OPERATIONS: lambda _, prompt: self._knowledge_base().handle_file_operation(prompt),
            Intent.COMPUTER_ACTIONS: lambda _, prompt: self.task_controller.handle(prompt),
            Intent.VISION: lambda _, prompt: self.vision_manager.analyze_screen(prompt),
            Intent.FINANCE: lambda *_: error_response("finance", "finance", "Finance service is not installed."),
            Intent.SYSTEM_COMMANDS: lambda *_: error_response("system", "system_commands", "System command handling is available in the CLI."),
        }

    def ask(self, user_input: str) -> dict[str, Any]:
        started_at = time.perf_counter()
        try:
            slash_response = self._handle_slash_command(user_input, started_at)
            if slash_response is not None:
                return slash_response

            classification = self._detect_memory_first(user_input)
            plan = self.provider_selector.select(classification.intent)
            handler = self.handlers.get(classification.intent, self._unknown)
            prompt, context_bundle = self.context_builder.augment_prompt(user_input, classification.intent)
            response = handler(classification, prompt)
            response.setdefault("data", {})
            if isinstance(response["data"], dict):
                response["data"]["context_debug"] = context_bundle.to_debug_dict()
                response["data"]["context_measurements"] = collect_context_measurements(context_bundle)
            if classification.intent not in {Intent.MEMORY, Intent.VISION}:
                self.memory_manager.observe_interaction(user_input, response)
            success_provider = self._success_provider(response, plan.provider)
            return self.formatter.format(response, classification, plan, started_at, success_provider)
        except Exception as exc:
            LOGGER.exception("SmartRouter failed.")
            classification = IntentResult(Intent.UNKNOWN, 0.0, user_input, "Ollama", "SmartRouter exception fallback.")
            plan = self.provider_selector.select(Intent.UNKNOWN)
            response = error_response("smart_router", "ask", "Sorry, something went wrong.", details=repr(exc))
            return self.formatter.format(response, classification, plan, started_at)

    def _handle_slash_command(self, user_input: str, started_at: float) -> dict[str, Any] | None:
        clean = user_input.strip()
        if not clean.startswith("/"):
            return None

        name, _, argument = clean.partition(" ")
        command = name.lower()
        prompt = argument.strip()
        command_map: dict[str, tuple[Intent, str, str, Callable[[str], dict[str, Any]]]] = {
            "/chat": (
                Intent.CONVERSATION,
                "Ollama",
                "Local Ollama chat requested by slash command.",
                lambda text: self.service_manager.ask("ollama", text),
            ),
            "/ollama": (
                Intent.CONVERSATION,
                "Ollama",
                "Local Ollama chat requested by slash command.",
                lambda text: self._ask_ollama_slash(text),
            ),
            "/groq": (
                Intent.REASONING,
                "Groq",
                "Groq provider requested by slash command.",
                lambda text: self.service_manager.ask("groq", text),
            ),
            "/grok": (
                Intent.REASONING,
                "Groq",
                "Groq provider requested by slash command.",
                lambda text: self.service_manager.ask("groq", text),
            ),
            "/hug": (
                Intent.TRANSLATION,
                "Hugging Face",
                "Hugging Face provider requested by slash command.",
                lambda text: self.service_manager.ask("huggingface", text),
            ),
            "/hf": (
                Intent.TRANSLATION,
                "Hugging Face",
                "Hugging Face provider requested by slash command.",
                lambda text: self.service_manager.ask("huggingface", text),
            ),
            "/nvidia": (
                Intent.REASONING,
                "NVIDIA",
                "NVIDIA NIM provider requested by slash command.",
                lambda text: self.service_manager.ask("nvidia", text),
            ),
            "/nim": (
                Intent.REASONING,
                "NVIDIA",
                "NVIDIA NIM provider requested by slash command.",
                lambda text: self.service_manager.ask("nvidia", text),
            ),
            "/wiki": (
                Intent.GENERAL_KNOWLEDGE,
                "Wikipedia",
                "Wikipedia provider requested by slash command.",
                lambda text: self.service_manager.ask("wikipedia", text, action="summary"),
            ),
            "/web": (
                Intent.WEB_INTELLIGENCE,
                "Web Intelligence",
                "Web intelligence requested by slash command.",
                lambda text: self.web_manager.answer(text),
            ),
            "/weather": (
                Intent.WEATHER,
                "Open-Meteo",
                "Weather provider requested by slash command.",
                lambda text: self._weather().handle(IntentResult(Intent.WEATHER, 1.0, text or "Current weather", "Open-Meteo", "Weather slash command.")),
            ),
            "/map": (
                Intent.MAPS,
                "OpenStreetMap",
                "Map provider requested by slash command.",
                lambda text: self.service_manager.ask("maps", text or "current location"),
            ),
            "/screen": (
                Intent.VISION,
                "AURA EYES",
                "AURA Eyes requested by slash command.",
                lambda text: self.vision_manager.analyze_screen(self._screen_prompt(text)),
            ),
        }

        route = command_map.get(command)
        if route is None:
            classification = IntentResult(Intent.UNKNOWN, 1.0, clean, "Ollama", "Unknown slash command.")
            plan = self.provider_selector.select(Intent.UNKNOWN)
            response = error_response("smart_router", "slash_command", f"Unknown command: {command}")
            return self.formatter.format(response, classification, plan, started_at)

        intent, provider, reason, handler = route
        if not prompt and command not in {"/weather", "/screen"}:
            classification = IntentResult(intent, 1.0, prompt, provider, reason)
            plan = self.provider_selector.select(intent)
            response = error_response("smart_router", "slash_command", f"Usage: {command} your question")
            return self.formatter.format(response, classification, plan, started_at)

        classification = IntentResult(intent, 1.0, prompt, provider, reason)
        plan = self.provider_selector.select(intent)
        response = handler(prompt)
        response.setdefault("data", {})
        if isinstance(response["data"], dict):
            response["data"]["slash_command"] = command
        return self.formatter.format(response, classification, plan, started_at, self._success_provider(response, plan.provider))

    def _ask_ollama_slash(self, prompt: str) -> dict[str, Any]:
        model, _, rest = prompt.partition(" ")
        if ":" in model and rest.strip():
            return self.service_manager.ask("ollama", rest.strip(), model=model)
        return self.service_manager.ask("ollama", prompt)

    @staticmethod
    def _screen_prompt(argument: str) -> str:
        lowered = argument.strip().lower()
        if lowered in {"text", "read", "ocr"}:
            return "Read the text on my screen."
        if lowered in {"describe", "description"}:
            return "What do you see on my screen?"
        if lowered in {"app", "application", "window"}:
            return "What application is currently open?"
        if lowered == "verify":
            return "Verify the current screen state."
        return argument.strip() or "Look at my screen."

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
            "nvidia": "NVIDIA",
            "wikipedia": "Wikipedia",
            "web": "Web Intelligence",
            "weather": "Open-Meteo",
            "maps": "OpenStreetMap",
            "math": "Local Math Engine",
            "memory": "MemoryManager",
            "knowledge": "Local Knowledge",
            "actions": "AURA HANDS",
            "agent": "AURA Agent Loop",
            "vision": "AURA EYES",
        }
        return names.get(provider, default)


def build_smart_router(service_manager: ServiceManager | None = None) -> SmartRouter:
    """Factory used by CLI and future desktop entry points."""
    return SmartRouter(service_manager=service_manager)
