"""Regression tests for explicit provider slash routing."""

from __future__ import annotations

import unittest
from typing import Any

from backend.router.smart_router import SmartRouter
from backend.utils.responses import success_response


class FakeServiceManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def ask(self, provider: str, prompt: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((provider, prompt, kwargs))
        if provider == "wikipedia":
            return success_response("wikipedia", "summary", {"title": prompt, "extract": "Wiki answer."}, "Wiki answer.")
        if provider == "groq":
            return success_response("groq", "chat_completion", {"content": "Groq answer.", "model": "fake-groq"}, "Groq answer.")
        if provider == "huggingface":
            return success_response("huggingface", "text_generation", {"content": "HF answer.", "model": "fake-hf"}, "HF answer.")
        if provider == "nvidia":
            return success_response("nvidia", "chat_completion", {"content": "NVIDIA answer.", "model": "fake-nvidia"}, "NVIDIA answer.")
        if provider == "ollama":
            return success_response("ollama", "chat", {"content": "Ollama answer.", "model": kwargs.get("model") or "auto-ollama"}, "Ollama answer.")
        return success_response(provider, "test", {"content": "ok"}, "ok")


class ProviderSlashRoutingTest(unittest.TestCase):
    def test_wiki_slash_routes_directly_to_wikipedia(self) -> None:
        service = FakeServiceManager()
        response = SmartRouter(service_manager=service).ask("/wiki Taj Mahal")

        self.assertEqual(service.calls[0][0], "wikipedia")
        self.assertEqual(service.calls[0][1], "Taj Mahal")
        self.assertEqual(response["route"]["provider"], "Wikipedia")
        self.assertEqual(response["route"]["intent"], "General Knowledge")

    def test_groq_and_hug_slashes_route_to_requested_provider(self) -> None:
        service = FakeServiceManager()
        router = SmartRouter(service_manager=service)

        groq = router.ask("/groq solve this reasoning task")
        hf = router.ask("/hug translate good morning")

        self.assertEqual(service.calls[0][0], "groq")
        self.assertEqual(service.calls[1][0], "huggingface")
        self.assertEqual(groq["route"]["provider"], "Groq")
        self.assertEqual(hf["route"]["provider"], "Hugging Face")

    def test_ollama_slash_can_pin_local_model(self) -> None:
        service = FakeServiceManager()
        response = SmartRouter(service_manager=service).ask("/ollama gemma3:4b explain local routing")

        provider, prompt, kwargs = service.calls[0]
        self.assertEqual(provider, "ollama")
        self.assertEqual(prompt, "explain local routing")
        self.assertEqual(kwargs["model"], "gemma3:4b")
        self.assertEqual(response["route"]["provider"], "Ollama")
        self.assertEqual(response["route"]["model"], "gemma3:4b")

    def test_nvidia_slashes_route_to_nim_provider(self) -> None:
        service = FakeServiceManager()
        router = SmartRouter(service_manager=service)

        nvidia = router.ask("/nvidia design an agent coding strategy")
        nim = router.ask("/nim reason through this architecture")

        self.assertEqual(service.calls[0][0], "nvidia")
        self.assertEqual(service.calls[1][0], "nvidia")
        self.assertEqual(nvidia["route"]["provider"], "NVIDIA")
        self.assertEqual(nim["route"]["provider"], "NVIDIA")


if __name__ == "__main__":
    unittest.main()
