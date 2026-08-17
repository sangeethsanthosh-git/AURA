"""Weather intent handler."""

from __future__ import annotations

from typing import Any

from backend.router.intent_classifier import IntentResult
from backend.router.service_manager import ServiceManager


class WeatherHandler:
    def __init__(self, services: ServiceManager) -> None:
        self.services = services

    def handle(self, classification: IntentResult) -> dict[str, Any]:
        return self.services.ask("weather", classification.query)
