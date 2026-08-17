# First Interim Presentation - AURA

## Slide 1 - Project Title

**AURA - Intelligent Personal Desktop Assistant**

Team Members: Add team member names  
Guide: Add guide name  
College: Add college name

## Slide 2 - Project Introduction

AURA is an offline-first intelligent desktop assistant that combines local AI, cloud AI, public APIs, and text-to-speech in a modular Python backend.

## Slide 3 - Problem Statement

Existing AI assistants are often cloud-dependent, privacy-sensitive, internet-dependent, and difficult to customize for desktop-first academic and research use.

## Slide 4 - Existing System

Most current assistants rely on cloud servers, closed ecosystems, and separate applications for chat, maps, weather, translation, and programming help.

## Slide 5 - Drawbacks

- Cloud dependency
- Privacy concerns
- Internet dependency
- High latency
- No offline AI
- Vendor lock-in
- Limited customization

## Slide 6 - Proposed System

AURA proposes a hybrid offline-first assistant using Ollama locally and online providers only when needed.

## Slide 7 - Objectives

- Provide local AI chat
- Integrate online AI providers
- Support live APIs
- Add Piper TTS
- Build modular router architecture
- Prepare for Electron, React, SQLite, RAG, and plugins

## Slide 8 - Technology Stack

- Python 3.12
- Ollama
- Groq API
- Hugging Face API
- Wikipedia API
- Open-Meteo
- OpenStreetMap
- Piper TTS
- Mermaid

## Slide 9 - Architecture Diagram

See `docs/architecture/Architecture_Diagram.md`.

## Slide 10 - Workflow Diagram

See `docs/workflow/Workflow_Diagram.md`.

## Slide 11 - DFD Level 0

See `docs/dfd/DFD_Level_0.md`.

## Slide 12 - DFD Level 1

See `docs/dfd/DFD_Level_1.md`.

## Slide 13 - DFD Level 2

See `docs/dfd/DFD_Level_2.md`.

## Slide 14 - Use Case Diagram

See `docs/uml/Use_Case_Diagram.md`.

## Slide 15 - Methods Used

- Intent classification
- Model routing
- Hybrid AI
- API integration
- Speech synthesis
- Error handling
- Logging
- Modular architecture

## Slide 16 - Modules Completed

- CLI
- Ollama
- Groq
- Hugging Face
- Wikipedia
- Weather
- Maps
- Piper
- Smart Router
- Service Manager

## Slide 17 - Current Outputs

- Local chat response
- Programming response through Groq
- Wikipedia summary
- Live weather
- Map search
- Translation
- Piper speech output

## Slide 18 - Screenshots

See `docs/screenshots/Screenshot_Guide.md`.

## Slide 19 - Future Scope

- Electron UI
- React frontend
- SQLite
- RAG
- Persistent memory
- Voice input
- Plugins
- Finance, calendar, notes, and file manager

## Slide 20 - Conclusion

AURA demonstrates an offline-first, modular, hybrid AI assistant backend suitable for an MCA mini project and future research expansion.
