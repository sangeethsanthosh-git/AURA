# Mini Project Report

# AURA - Intelligent Personal Desktop Assistant

## Abstract

AURA is an offline-first intelligent desktop assistant that integrates local LLM inference, cloud AI providers, public APIs, and speech synthesis. The system uses a modular Python backend with a Smart Router to classify intent, select providers, apply fallbacks, and return structured responses.

## Introduction

AI assistants are increasingly useful for personal productivity, programming, learning, and information retrieval. However, many assistants depend entirely on cloud services. AURA addresses this by making local AI the foundation while still supporting online providers and live APIs when required.

## Literature Survey

Existing assistants include cloud chatbots, voice assistants, and task-specific web applications. These systems demonstrate strong natural language capabilities but often lack offline availability, transparent routing, and extensibility. Local LLM tools such as Ollama make offline AI practical, while public APIs such as Wikipedia, Open-Meteo, and OpenStreetMap support live information retrieval.

## Existing System

Existing systems are commonly cloud-first, vendor-controlled, and fragmented across multiple applications.

## Drawbacks

- Cloud dependency
- Privacy issues
- Internet dependency
- High latency
- Limited offline AI
- Limited customization
- Vendor lock-in

## Proposed System

AURA proposes a hybrid desktop assistant using local AI, cloud AI, live APIs, smart routing, and speech output. The architecture is modular and research-friendly.

## Architecture

The system contains a CLI frontend, Smart Router, Service Manager, provider services, response formatter, and Piper TTS. Future architecture includes Electron, React, SQLite, memory, RAG, and plugins.

## Data Flow Diagrams

DFD Level 0, Level 1, and Level 2 are available in `docs/dfd/`.

## Workflow

The workflow begins with user input, followed by language detection, intent classification, provider selection, AI/API execution, response formatting, display, and speech.

## Methods

The project uses intent classification, hybrid AI routing, model routing, API integration, prompt engineering, logging, error handling, and modular design.

## Modules

Completed modules include CLI, Ollama, Groq, Hugging Face, Wikipedia, weather, maps, Piper TTS, Smart Router, Service Manager, logging, and error handling.

## Implementation

The implementation uses Python services for each provider. The Smart Router coordinates routing and fallback logic. API keys are loaded from environment variables.

## Results

The current backend can answer local chat, programming, translation, Wikipedia, weather, and maps queries. Piper TTS speaks only the assistant message, not metadata.

## Screenshots

Screenshot instructions are available in `docs/screenshots/Screenshot_Guide.md`.

## Future Scope

- Electron + React UI
- SQLite storage
- RAG
- Persistent memory
- Voice input
- Calendar
- Notes
- Finance APIs
- Plugin system

## Conclusion

AURA successfully demonstrates a modular offline-first AI assistant backend. The system is suitable for an MCA mini project and can be expanded into a full research project.

## References

- Ollama documentation
- Groq API documentation
- Hugging Face documentation
- Wikipedia API documentation
- Open-Meteo documentation
- OpenStreetMap Nominatim documentation
- Piper TTS project
