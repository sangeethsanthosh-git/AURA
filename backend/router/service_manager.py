"""Central service manager for AURA backend integrations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from conversation_manager import ConversationManager

from backend.services.groq_service import GroqService
from backend.services.huggingface_service import HuggingFaceService
from backend.services.location_service import LocationService
from backend.services.maps_service import MapsService
from backend.services.nvidia_service import NvidiaService
from backend.services.ollama_service import OllamaService
from backend.services.weather_service import WeatherService
from backend.services.wikipedia_service import WikipediaService
from backend.utils.responses import error_response

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderRegistration:
    """Describes how to construct and invoke a provider service."""

    factory: Callable[[], Any]
    dispatcher: Callable[[Any, str, dict[str, Any]], dict[str, Any]]


class ServiceManager:
    """Single entry point for CLI, future Electron UI, and research modules."""

    def __init__(self, conversation_manager: ConversationManager | None = None) -> None:
        self._conversation_manager = conversation_manager
        self._services: dict[str, Any] = {}
        self._providers: dict[str, ProviderRegistration] = {}
        self._register_default_providers()

    def ask(self, provider: str, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """Dispatch a user request to the requested provider."""
        provider_key = provider.lower().strip()
        LOGGER.info("ServiceManager dispatch provider=%s", provider_key)

        aliases = {"hf": "huggingface", "wiki": "wikipedia", "map": "maps", "nim": "nvidia"}
        provider_key = aliases.get(provider_key, provider_key)
        registration = self._providers.get(provider_key)
        if registration:
            return registration.dispatcher(self._service(provider_key), prompt, kwargs)

        return error_response("service_manager", "ask", f"Unsupported provider: {provider}")

    def register_provider(
        self,
        name: str,
        factory: Callable[[], Any],
        dispatcher: Callable[[Any, str, dict[str, Any]], dict[str, Any]],
    ) -> None:
        """Register a provider without changing ServiceManager dispatch logic."""
        self._providers[name] = ProviderRegistration(factory=factory, dispatcher=dispatcher)

    def stream(self, provider: str, prompt: str, **kwargs: Any):
        """Dispatch streaming requests for providers that support streaming."""
        provider_key = provider.lower().strip()
        if provider_key != "groq":
            yield error_response(provider_key, "stream", "Streaming is currently supported only for Groq.")
            return
        yield from self._service("groq").stream_chat_completion(prompt, **kwargs)

    def _service(self, name: str) -> Any:
        if name not in self._services:
            self._services[name] = self._providers[name].factory()
        return self._services[name]

    def _register_default_providers(self) -> None:
        self.register_provider(
            "ollama",
            lambda: OllamaService(self._conversation_manager),
            lambda service, prompt, kwargs: service.chat(prompt, model=kwargs.get("model")),
        )
        self.register_provider(
            "groq",
            GroqService,
            lambda service, prompt, kwargs: service.chat_completion(prompt, **kwargs),
        )
        self.register_provider(
            "huggingface",
            HuggingFaceService,
            lambda service, prompt, kwargs: service.text_generation(prompt, **kwargs),
        )
        self.register_provider(
            "nvidia",
            NvidiaService,
            lambda service, prompt, kwargs: service.chat_completion(prompt, **kwargs),
        )
        self.register_provider(
            "wikipedia",
            WikipediaService,
            lambda service, prompt, kwargs: self._wikipedia(service, prompt, kwargs.pop("action", "summary"), **kwargs),
        )
        self.register_provider(
            "weather",
            WeatherService,
            lambda service, prompt, kwargs: self._weather(service, prompt, kwargs.pop("action", "current_weather"), **kwargs),
        )
        self.register_provider(
            "location",
            LocationService,
            lambda service, prompt, kwargs: service.current_location(),
        )
        self.register_provider(
            "maps",
            MapsService,
            lambda service, prompt, kwargs: self._maps(service, prompt, kwargs.pop("action", "search_location"), **kwargs),
        )

    def _wikipedia(self, service: WikipediaService, prompt: str, action: str, **kwargs: Any) -> dict[str, Any]:
        if action == "search":
            return service.search(prompt, **kwargs)
        if action == "page":
            return service.page(prompt)
        if action == "summary":
            return service.summary(prompt)
        if action == "handle_disambiguation":
            return service.handle_disambiguation(prompt)
        return error_response("wikipedia", action, f"Unsupported Wikipedia action: {action}")

    def _weather(self, service: WeatherService, prompt: str, action: str, **kwargs: Any) -> dict[str, Any]:
        if action == "forecast":
            return service.forecast(prompt, **kwargs)
        if action == "current_weather":
            return service.current_weather(prompt)
        return error_response("weather", action, f"Unsupported weather action: {action}")

    def _maps(self, service: MapsService, prompt: str, action: str, **kwargs: Any) -> dict[str, Any]:
        if action == "search_location":
            return service.search_location(prompt, **kwargs)
        if action == "reverse_geocode":
            latitude = kwargs.get("latitude")
            longitude = kwargs.get("longitude")
            if latitude is None or longitude is None:
                return error_response("maps", action, "latitude and longitude are required.")
            return service.reverse_geocode(float(latitude), float(longitude))
        return error_response("maps", action, f"Unsupported maps action: {action}")
