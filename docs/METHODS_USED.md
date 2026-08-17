# Methods Used

## Intent Classification

AURA uses an intent classifier to identify whether a request is conversation, programming, mathematics, reasoning, knowledge, weather, maps, translation, memory, or another task. The current router uses priority-based classification with keyword signals and lightweight semantic similarity.

## Model Routing

The Model Router selects local Ollama models based on language and configured model preferences. The Smart Router selects the provider based on user intent.

## Prompt Engineering

Prompts are structured according to task type. For example, Wikipedia content can be passed to Ollama for natural explanation, while programming tasks are routed to Groq with fallback to Ollama.

## Hybrid AI

AURA combines local AI and cloud AI. Ollama supports offline-first behavior, while Groq and Hugging Face provide online model capabilities when appropriate.

## API Integration

The backend integrates Wikipedia, Open-Meteo, OpenStreetMap Nominatim, Groq, and Hugging Face through independent service classes. Each service returns structured responses.

## Speech Synthesis

Piper TTS is used for local text-to-speech. Response metadata is separated from assistant messages so TTS speaks only natural assistant output.

## Error Handling

Services return user-friendly errors while logging diagnostic details. Weather requests include step-by-step logging for geocoding, coordinates, HTTP status, JSON parsing, and formatted output.

## Logging

The system logs routing decisions, provider selection, fallback behavior, execution time, success state, and service-level diagnostics.

## Modular Architecture

The backend separates services, routing, configuration, utilities, and tests. This supports SOLID design and future expansion.
