# Proposed System

AURA proposes an offline-first intelligent desktop assistant that combines local AI, cloud AI, free public APIs, speech synthesis, and modular routing.

## Offline-First

AURA uses Ollama as the primary local AI provider. This allows core conversational features to work locally and supports privacy-focused usage.

## Hybrid AI

The system combines local and online AI providers. Local AI handles conversation and fallback tasks, while cloud providers such as Groq and Hugging Face support programming, translation, and higher-performance inference.

## Local LLM

Ollama provides local model execution. The Model Router selects configured models based on language and task needs.

## Cloud AI

Groq and Hugging Face are integrated as optional online providers. API keys are loaded from environment variables and are never hardcoded.

## Voice Assistant

Piper TTS converts assistant responses into speech. Metadata is kept separate from assistant messages so speech output remains natural.

## Modular Architecture

The backend is divided into services, router modules, utilities, and configuration. This supports testability and future research development.

## Plugin System

The future plugin system can add providers such as finance, calendar, email, GitHub, file management, and vision without rewriting the Smart Router.

## Desktop Application

The planned Electron + React frontend will consume the same backend routing interface used by the current CLI.

## Hybrid Routing

The Smart Router classifies user intent, selects providers, applies fallbacks, and returns structured responses with metadata.

## Privacy

Local AI is preferred for private and conversational tasks. Live services are used only when the user needs live knowledge, weather, maps, translation, or cloud reasoning.

## Scalability

The architecture separates intent classification, provider selection, fallback handling, and response formatting, making it suitable for expansion.

## Future Expansion

Planned modules include SQLite persistence, memory, RAG, notes, calendar, finance APIs, voice input, file manager, and plugin support.
