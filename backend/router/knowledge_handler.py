"""General knowledge intent handler."""

from __future__ import annotations

from typing import Any

from backend.router.fallback_manager import FallbackManager
from backend.router.intent_classifier import IntentResult
from backend.router.service_manager import ServiceManager


class KnowledgeHandler:
    def __init__(self, services: ServiceManager, fallbacks: FallbackManager) -> None:
        self.services = services
        self.fallbacks = fallbacks

    def handle(self, classification: IntentResult, original_prompt: str) -> dict[str, Any]:
        return self.fallbacks.run([
            ("Wikipedia", lambda: self.services.ask("wikipedia", classification.query, action="summary")),
            ("Ollama", lambda: self.services.ask("ollama", f"Live information unavailable. {original_prompt}")),
        ])
