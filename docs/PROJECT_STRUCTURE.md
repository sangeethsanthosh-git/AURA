# Project Structure

```text
AURA/
├── app.py
├── aura_config.py
├── config.py
├── conversation_manager.py
├── language_manager.py
├── model_router.py
├── ollama_client.py
├── speech_manager.py
├── tts_manager.py
├── backend/
│   ├── config/
│   ├── router/
│   ├── services/
│   ├── tests/
│   └── utils/
├── docs/
│   ├── architecture/
│   ├── dfd/
│   ├── diagrams/
│   ├── presentation/
│   ├── reports/
│   ├── screenshots/
│   ├── uml/
│   └── workflow/
├── output/
├── tools/
└── voices/
```

## Root Files

- `app.py`: CLI entry point.
- `aura_config.py`: existing local configuration.
- `config.py`: backend configuration compatibility entry point.
- `conversation_manager.py`: manages local conversation flow.
- `language_manager.py`: handles language detection and switching.
- `model_router.py`: selects local Ollama model based on language.
- `ollama_client.py`: communicates with Ollama.
- `tts_manager.py`: Piper TTS integration.

## backend/config

Loads environment variables and `.env` settings for API keys, debug settings, provider URLs, and runtime options.

## backend/services

Contains independent provider adapters:

- Ollama
- Groq
- Hugging Face
- Wikipedia
- Weather
- Maps
- Location

## backend/router

Contains routing intelligence:

- Smart Router
- Intent Classifier
- Provider Selector
- Fallback Manager
- Response Formatter
- Memory Manager
- Math Engine
- Intent handlers

## backend/utils

Reusable HTTP and response helpers.

## backend/tests

Smoke and regression tests for routing, weather, response splitting, and provider behavior.

## docs

Project documentation, reports, diagrams, presentation notes, screenshot guide, and architecture references.
