"""Programming intent handler."""

from __future__ import annotations

from typing import Any

from backend.router.fallback_manager import FallbackManager
from backend.router.service_manager import ServiceManager


class ProgrammingHandler:
    def __init__(self, services: ServiceManager, fallbacks: FallbackManager) -> None:
        self.services = services
        self.fallbacks = fallbacks

    def handle(self, prompt: str) -> dict[str, Any]:
        return self.fallbacks.run([
            ("NVIDIA", lambda: self.services.ask("nvidia", prompt)),
            ("Groq", lambda: self.services.ask("groq", prompt)),
            ("Ollama", lambda: self.services.ask("ollama", prompt)),
        ])
