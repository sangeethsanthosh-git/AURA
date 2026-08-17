# AURA - Intelligent Personal Desktop Assistant

## Project Overview

AURA is an offline-first intelligent desktop assistant designed to provide local AI conversation, hybrid online AI access, live knowledge services, weather, maps, and speech output from one modular Python backend. The current implementation runs through a CLI and is structured so it can later support an Electron + React desktop interface.

## Problem Statement

Most personal AI assistants depend heavily on cloud services, require constant internet access, and provide limited control over routing, privacy, customization, and local intelligence. Students, developers, and everyday desktop users need an assistant that can work locally first while still using online services when live data or high-performance cloud AI is needed.

## Motivation

The project is motivated by the need for a privacy-aware, extensible, research-friendly desktop assistant. AURA combines local LLMs through Ollama with optional online providers such as Groq and Hugging Face, while also integrating free APIs like Wikipedia, Open-Meteo, and OpenStreetMap.

## Objectives

- Build an offline-first AI assistant backend.
- Route user requests intelligently using intent classification.
- Use local AI whenever suitable.
- Use live APIs only when needed.
- Provide text-to-speech output using Piper.
- Maintain a modular architecture for future research expansion.
- Prepare the system for Electron, React, SQLite, RAG, memory, and plugin support.

## Scope

The current scope covers the Python backend, CLI interaction, smart routing, service integrations, response formatting, logging, and TTS. The frontend, persistent memory, SQLite storage, RAG, calendar, notes, finance APIs, and plugin system are future extensions.

## Features

- CLI interface
- Ollama local LLM integration
- Groq API integration
- Hugging Face API integration
- Wikipedia API integration
- Open-Meteo weather integration
- OpenStreetMap Nominatim maps integration
- Piper text-to-speech
- Smart AI Router
- Intent Classifier
- Service Manager
- Response Formatter
- Language detection and model routing
- Logging and error handling

## Technologies Used

- Python 3.12
- Ollama
- Groq API
- Hugging Face API
- Wikipedia API
- Open-Meteo API
- OpenStreetMap Nominatim
- Piper TTS
- Markdown
- Mermaid diagrams

## Expected Outcome

AURA is expected to provide a working offline-first AI assistant backend that demonstrates hybrid AI routing, modular service integration, and a scalable foundation for a full desktop assistant and future research project.
