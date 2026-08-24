"""Provider selection for classified intents."""

from __future__ import annotations

from dataclasses import dataclass

from backend.config.config import settings
from backend.router.intent_classifier import Intent


@dataclass(frozen=True)
class ProviderPlan:
    """Primary provider plus ordered fallbacks for an intent."""

    provider: str
    source: str
    model: str
    fallbacks: tuple[str, ...] = ()


class ProviderSelector:
    """Maps intents to providers without embedding routing code in SmartRouter."""

    def select(self, intent: Intent) -> ProviderPlan:
        plans = {
            Intent.MEMORY: ProviderPlan("MemoryManager", "Session Memory", "Local Memory"),
            Intent.MATHEMATICS: ProviderPlan("Local Math Engine", "Python Math Engine", "Python"),
            Intent.REASONING: ProviderPlan("Groq", "Groq API", settings.groq_model, ("Ollama",)),
            Intent.PROGRAMMING: ProviderPlan("Groq", "Groq API", settings.groq_model, ("Ollama",)),
            Intent.TRANSLATION: ProviderPlan("Hugging Face", "Hugging Face Router", settings.hf_model, ("Ollama",)),
            Intent.GENERAL_KNOWLEDGE: ProviderPlan("Wikipedia", "Wikipedia API", "Ollama", ("Ollama",)),
            Intent.WEB_INTELLIGENCE: ProviderPlan("Web Intelligence", "Bounded Web Search", "Local/Ollama"),
            Intent.WEATHER: ProviderPlan("Open-Meteo", "Live Weather API", "None"),
            Intent.LOCATION: ProviderPlan("OpenStreetMap", "OpenStreetMap Nominatim", "None"),
            Intent.MAPS: ProviderPlan("OpenStreetMap", "OpenStreetMap Nominatim", "None"),
            Intent.CONVERSATION: ProviderPlan("Ollama", "Local AI", "Ollama"),
            Intent.DOCUMENTS: ProviderPlan("Local Knowledge", "Local Knowledge Base", "None"),
            Intent.RAG: ProviderPlan("Local Knowledge", "Local Knowledge Base", "None"),
            Intent.FILE_OPERATIONS: ProviderPlan("Local Knowledge", "Temporary Document Context", "None"),
            Intent.COMPUTER_ACTIONS: ProviderPlan("AURA Agent Loop", "Bounded Eyes + Hands Task Controller", "None"),
            Intent.VISION: ProviderPlan("AURA EYES", "On-Demand Screen Vision", "Local Vision"),
            Intent.FINANCE: ProviderPlan("Finance service is not installed.", "Not installed", "None"),
            Intent.SYSTEM_COMMANDS: ProviderPlan("System", "Local CLI", "None"),
        }
        return plans.get(intent, ProviderPlan("Ollama", "Local AI", "Ollama"))
