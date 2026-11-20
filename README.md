# AURA — Next-Gen AI Desktop Assistant & Virtual Companion

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20x64-blue.svg)](https://microsoft.com)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-yellow.svg)](https://python.org)
[![Electron](https://img.shields.io/badge/Electron-45.2.3-teal.svg)](https://electronjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Status](https://img.shields.io/badge/Tests-165%2F165%20Passing-brightgreen.svg)]()

> **A local-first, privacy-respecting AI desktop voice and automation assistant for Windows 11.**  
> Features an independent **Kawaii Pixel Cat Paw** virtual assistant hand that interacts directly with your desktop without touching or modifying your actual mouse cursor!

---

## 🌟 Key Features

### 🐾 1. Kawaii Pixel Cat Paw Independent Virtual Hand
- **Two Distinct Cursors**:
  - **Your Cursor**: Remains your standard Windows mouse cursor. Never changed or overridden.
  - **AURA's Hand**: An independent, transparent always-on-top virtual hand (Kawaii Pixel Cat Paw).
- **Physical Desktop Actions**: Appears when performing automated tasks (searching Google, opening applications, clicking YouTube thumbnails, typing into inputs) with animated cat paw frames, spring physics gliding, and click-paw pulses.
- **Virtual Keyboard HUD**: Glassmorphic on-screen keyboard visualizer showing real-time typing preview and key depressions with zero dropped characters.
- **Custom Hand Skin Library**: Install and customize downloaded `.cur`, `.ani`, `.gif`, `.png` or zipped cursor packs directly in Assistant Settings.

### 🎙️ 2. Voice & Speech Architecture
- **Instant Push-to-Talk**: Tap `[Spacebar]` or `[Ctrl+Shift+Space]` anywhere on your desktop.
- **Continuous Wake-Word**: Hands-free `"Hey AURA"` / `"AURA"` activation powered by OpenWakeWord.
- **Acoustic Loopback Prevention**: Automatically drops mic frames during speech output to prevent self-triggering and echo.
- **Speech-to-Text (STT)**: Offline CPU-accelerated Faster-Whisper (`int8` quantization, 0MB GPU VRAM overhead).
- **Humanized TTS**: Qwen3-TTS (24 kHz expressive voice) with automatic fallback to Piper ONNX (`en_US-lessac-medium`) and Microsoft Edge TTS.

### 💻 3. Native Windows 11 Automation
- **Web & Media**: Natural Google and YouTube searching, dropdown suggestion filtering, YouTube/Spotify playback control (play/pause/next/prev), and precise timeline scrubber seeking (e.g., *"seek to 50%"*, *"jump forward 30 seconds"*).
- **System Diagnostics**: Check CPU, RAM, battery levels, storage drives, and network health.
- **Volume & Audio**: Hardware volume control (`mute`, `unmute`, `set volume to X%`).
- **Application Control**: Launch, switch, resize, minimize, and close native desktop applications.

### 🧠 4. Dynamic Personality & Memory
- Context-aware social engine with 6 adaptive profiles: **Friend**, **Teacher**, **Normal**, **Professional**, **Supportive**, and **Mischievous**.
- Remembers user context, projects, and tone preferences across sessions in local SQLite.

### 📬 5. Email Reminders & Notifications
- Official Google Gmail OAuth integration with least-privilege `gmail.send` scope.
- Natural language reminder scheduling: *"Remind me tomorrow at 9 AM about my presentation"*.
- Daily digest emails and important note summaries delivered to your personal inbox.

### 🛡️ 6. Zero-Trust Security Sandbox
- 4-Tier Security policy: read-only operations executed freely, critical system operations require explicit user approval.
- Built-in prompt injection defense and comprehensive security audit logging.

---

## 🚀 Quick Start Guide

### Option A: One-Click Launch (Recommended)
If you already ran setup, simply double-click:
```text
AURA.exe
```
This native launcher automatically starts Ollama, spins up the FastAPI backend daemon, and opens the desktop assistant window.

---

### Option B: Fresh Setup for New Users / Clone from GitHub

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/AURA.git
   cd AURA
   ```

2. **Run One-Click Setup**:
   Double-click `setup.bat` (or execute in PowerShell):
   ```cmd
   setup.bat
   ```
   *What `setup.bat` does:*
   - Verifies Python 3.10+, Node.js, and Ollama.
   - Creates a dedicated `.venv` virtual environment and installs `requirements.txt`.
   - Builds the React + Vite frontend bundle and Electron packages.
   - Compiles the native `AURA.exe` Windows launcher with embedded app icon.
   - Generates `.env` from `.env.example`.

3. **Launch AURA**:
   Double-click `AURA.exe` or run:
   ```cmd
   Launch_AURA_Desktop.bat
   ```

---

## 📦 Building Standalone Installer for Distribution

To generate a standalone Windows installer (`AURA Setup 1.0.0.exe`) suitable for GitHub Releases:

```cmd
scripts\build_release.bat
```
The resulting installer will be created in `release\AURA-Setup.exe` (and `frontend\dist-electron\`). Users can install AURA directly without needing Git.

---

## 🧪 Running Automated Tests

Run the full backend test suite (165 passing tests):
```powershell
.\.venv\Scripts\python.exe -m unittest discover backend/tests
```

Run specific test modules:
```powershell
# Virtual Hand & Cat Paw Cursor System Tests
.\.venv\Scripts\python.exe -m unittest backend.tests.test_virtual_hand_system

# Media & Natural Search Tests
.\.venv\Scripts\python.exe -m unittest backend.tests.test_media_search_playback_fixes

# Email & Reminder System Tests
.\.venv\Scripts\python.exe -m unittest backend.tests.test_reminder_service
```

---

## ⚙️ Configuration (.env)

Customize AURA's models, voices, and hardware settings in `.env`:
```ini
# Ollama LLM
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b

# Whisper STT (CPU INT8)
WHISPER_MODEL_SIZE=base.en
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8

# Text-to-Speech Engine
TTS_ENGINE=piper
PIPER_MODEL_PATH=assets/voices/en_US-lessac-medium.onnx
```

---

## 📄 License
This project is licensed under the MIT License.
