"""System reliability audit regressions for AURA ASUS V1."""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication

from app import build_assistant_output, normalize_cli_command
from backend.memory.daily_memory import DailyMemory
from backend.memory.memory_manager import MemoryManager
from backend.memory.memory_retriever import MemoryRetriever
from backend.router.intent_classifier import IntentClassifier
from backend.router.intent_types import Intent
from backend.router.smart_router import SmartRouter
from backend.utils.responses import error_response, success_response
from ui.controller.aura_controller import AuraController
from ui.main_window import MainWindow


class FakeServiceManager:
    """Deterministic service manager for router/provider failure tests."""

    def __init__(self, fail: set[str] | None = None, delay: float = 0.0) -> None:
        self.fail = fail or set()
        self.delay = delay
        self.calls: list[tuple[str, str]] = []

    def ask(self, provider: str, prompt: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((provider, prompt))
        if self.delay:
            time.sleep(self.delay)
        if provider in self.fail:
            return error_response(provider, "fake", f"{provider} unavailable")
        if provider == "ollama":
            return success_response("ollama", "chat", {"content": "Local fallback response.", "model": "fake-ollama"}, "Local fallback response.")
        if provider == "groq":
            return success_response("groq", "chat_completion", {"content": "Programming response.", "model": "fake-groq"}, "Programming response.")
        if provider == "huggingface":
            return success_response("huggingface", "text_generation", {"content": "Translated text.", "model": "fake-hf"}, "Translated text.")
        if provider == "wikipedia":
            return success_response("wikipedia", "summary", {"title": prompt, "summary": "Alan Turing was a mathematician."}, "Alan Turing was a mathematician.")
        if provider == "weather":
            return success_response("weather", "current_weather", {"location": {"name": "Kochi"}, "current_weather": {"temperature": 27}}, "Weather for Kochi\nTemperature: 27 deg C")
        if provider == "maps":
            return success_response("maps", "search_location", {"results": [{"display_name": "Delhi", "latitude": "28.6", "longitude": "77.2"}]}, "Delhi")
        return error_response(provider, "fake", "unsupported fake provider")


def check(condition: bool, label: str, failures: list[str]) -> None:
    if not condition:
        failures.append(label)


def main() -> int:
    failures: list[str] = []

    classifier = IntentClassifier()
    intent_cases = {
        "Hello there": Intent.CONVERSATION,
        "Remember that I prefer Python.": Intent.MEMORY,
        "What is my name?": Intent.MEMORY,
        "Write a Python function.": Intent.PROGRAMMING,
        "What is 587 × 932?": Intent.MATHEMATICS,
        "Solve this logic puzzle.": Intent.REASONING,
        "Who is Alan Turing?": Intent.GENERAL_KNOWLEDGE,
        "Weather in Kochi.": Intent.WEATHER,
        "Locate Delhi.": Intent.MAPS,
        "Translate Good Morning to Malayalam.": Intent.TRANSLATION,
        "Current Bitcoin price.": Intent.FINANCE,
        "Summarize pdf notes.": Intent.FILE_OPERATIONS,
        "Search my knowledge base.": Intent.RAG,
        "version": Intent.SYSTEM_COMMANDS,
        "purple bicycle quietly": Intent.UNKNOWN,
    }
    for prompt, expected in intent_cases.items():
        result = classifier.classify(prompt)
        check(result.intent == expected, f"intent {prompt!r}: got {result.intent}, expected {expected}", failures)
        if expected != Intent.UNKNOWN:
            check(result.confidence >= 0.60, f"low confidence for {prompt!r}: {result.confidence}", failures)

    ambiguous = classifier.classify("How do I get to Delhi?")
    check(ambiguous.intent != Intent.MAPS, "ambiguous travel request was treated as simple Maps lookup", failures)

    router = SmartRouter(service_manager=FakeServiceManager())
    math_cases = {
        "587 × 932": 547084,
        "123 + 456": 579,
        "100 / 4": 25,
        "2^10": 1024,
        "sqrt(144)": 12,
        "10% of 500": 50,
    }
    for prompt, expected in math_cases.items():
        response = router.ask(prompt)
        route = response.get("route", {})
        check(response.get("data", {}).get("result") == expected, f"math {prompt!r} returned {response.get('data')}", failures)
        check(route.get("execution_source") == "Python Math Engine", f"math source metadata wrong for {prompt!r}", failures)
        check(route.get("llm_used") is False, f"math llm_used metadata wrong for {prompt!r}", failures)
        check(route.get("llm_provider") is None, f"math unexpectedly used LLM for {prompt!r}", failures)

    div_zero = router.ask("2 / 0")
    div_route = div_zero.get("route", {})
    check(not div_zero.get("ok"), "division by zero should fail cleanly", failures)
    check("Cannot divide by zero" in str((div_zero.get("error") or {}).get("message")), "division by zero message was not specific", failures)
    check(div_route.get("execution_source") == "Python Math Engine", "division by zero execution source wrong", failures)
    check(div_route.get("llm_used") is False, "division by zero unexpectedly used LLM", failures)
    invalid = router.ask("calculate banana")
    check(invalid.get("route", {}).get("intent") == "Unknown", "invalid math-like text should not hit Python Math Engine", failures)

    provider_router = SmartRouter(service_manager=FakeServiceManager(fail={"groq", "huggingface"}))
    ollama = provider_router.ask("Hello there")
    ollama_route = ollama.get("route", {})
    check(ollama_route.get("llm_used") is True, f"Ollama llm_used metadata wrong: {ollama_route}", failures)
    check(ollama_route.get("llm_provider") == "Ollama", f"Ollama llm_provider metadata wrong: {ollama_route}", failures)
    check(ollama_route.get("model") == "fake-ollama", f"Ollama model metadata wrong: {ollama_route}", failures)
    programming = provider_router.ask("Write a Python function.")
    programming_route = programming.get("route", {})
    check(programming.get("ok") and programming.get("provider") == "ollama", "programming fallback to Ollama failed", failures)
    check(programming_route.get("llm_used") is True and programming_route.get("llm_provider") == "Ollama", f"fallback metadata wrong: {programming_route}", failures)
    check(programming_route.get("execution_source") == "Local AI", f"fallback execution source wrong: {programming_route}", failures)
    check(programming_route.get("fallback") == "Ollama", f"actual fallback metadata wrong: {programming_route}", failures)
    translation = provider_router.ask("Translate Good Morning to Malayalam.")
    check(translation.get("ok") and translation.get("provider") == "ollama", "translation fallback to Ollama failed", failures)
    knowledge = provider_router.ask("Who is Alan Turing?")
    knowledge_route = knowledge.get("route", {})
    check(knowledge.get("ok") and knowledge.get("provider") == "wikipedia", "knowledge did not use Wikipedia first", failures)
    check(knowledge_route.get("execution_source") == "Wikipedia API", f"Wikipedia source metadata wrong: {knowledge_route}", failures)
    check(knowledge_route.get("llm_used") is False, f"Wikipedia llm_used metadata wrong: {knowledge_route}", failures)
    check(knowledge_route.get("llm_provider") is None, f"Wikipedia llm_provider metadata wrong: {knowledge_route}", failures)
    check(knowledge_route.get("model") == "None", f"Wikipedia model metadata wrong: {knowledge_route}", failures)
    check(knowledge_route.get("fallback") == "None", f"unused fallback metadata wrong: {knowledge_route}", failures)
    weather = provider_router.ask("Weather in Kochi.")
    check(weather.get("ok") and weather.get("provider") == "weather", "weather did not use weather service", failures)
    maps = provider_router.ask("Locate Delhi.")
    check(maps.get("ok") and maps.get("provider") == "maps", "maps did not use maps service", failures)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        memory = MemoryManager(path=root / "memory.json", daily_root=root / "daily")
        memory.retriever = MemoryRetriever(DailyMemory(root / "daily"))
        memory.handle("Remember that I prefer Python.")
        memory.handle("Remember that I prefer Python.")
        check(len([m for m in memory.data.long_term if "python" in m.content.lower()]) == 1, "duplicate memory was stored", failures)
        memory.handle("Remember that I now prefer Java.")
        active_preferences = [m for m in memory.data.long_term if m.category == "PREFERENCE" and m.status == "ACTIVE"]
        check(len(active_preferences) == 1 and "java" in active_preferences[0].content.lower(), "preference contradiction not superseded", failures)
        memory.handle("Forget that I prefer Java.")
        check(not [m for m in memory.data.long_term if m.category == "PREFERENCE" and m.status == "ACTIVE"], "forget did not remove active preference", failures)
        memory.observe_interaction("Hello, how are you?")
        check(not memory.data.conversation, "casual conversation persisted unexpectedly", failures)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        memory_router = SmartRouter(
            service_manager=FakeServiceManager(),
            memory_manager=MemoryManager(path=root / "memory.json", daily_root=root / "daily"),
        )
        remember = memory_router.ask("Remember that I prefer Python.")
        review = memory_router.ask("What do you remember about me?")
        memory_router.ask("Tell me about Python.")
        session = memory_router.ask("What were we discussing?")
        check(remember.get("route", {}).get("execution_source") == "Long-Term Memory", f"remember source wrong: {remember.get('route')}", failures)
        check(review.get("route", {}).get("execution_source") == "Long-Term Memory", f"review source wrong: {review.get('route')}", failures)
        check(session.get("route", {}).get("execution_source") == "Session Memory", f"session source wrong: {session.get('route')}", failures)

    output = build_assistant_output(error_response("ollama", "chat", "Could not connect to Ollama at http://localhost:11434."))
    check("Traceback" not in output.assistant_message, "CLI output exposed stack trace", failures)
    check(normalize_cli_command("/weather Kochi") == ("Weather", "What is the weather in Kochi?"), "CLI slash command changed", failures)

    app = QApplication.instance() or QApplication([])
    controller = AuraController(router=SmartRouter(service_manager=FakeServiceManager(delay=0.1)))
    window = MainWindow(controller)
    started = time.perf_counter()
    window.send_message("587 × 932")
    app.processEvents()
    check(time.perf_counter() - started < 0.05, "GUI send_message blocked main thread", failures)
    deadline = time.time() + 2.0
    while time.time() < deadline and window.request_thread is not None:
        app.processEvents()
        time.sleep(0.01)
    check(window.request_thread is None, "GUI worker did not finish", failures)
    check(bool(controller.activities), "GUI activity metadata was not recorded", failures)
    window.close()

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print("PASS system reliability audit regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
