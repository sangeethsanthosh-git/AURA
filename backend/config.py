"""
Configuration settings for AURA Voice Assistant.
"""

from pathlib import Path
import os

# Root directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Ollama LLM Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_CONTEXT_LENGTH = int(os.getenv("OLLAMA_CONTEXT_LENGTH", "4096"))
OLLAMA_REQUEST_TIMEOUT = float(os.getenv("OLLAMA_REQUEST_TIMEOUT", "30.0"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "15m")

# Faster-Whisper STT Configuration (CPU with INT8 for 0MB VRAM overhead)
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base.en")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_CPU_THREADS = int(os.getenv("WHISPER_CPU_THREADS", "4"))
WHISPER_BEAM_SIZE = int(os.getenv("WHISPER_BEAM_SIZE", "1"))

# Wake-Word & Activation Configuration
WAKE_WORD_PHRASE = os.getenv("WAKE_WORD_PHRASE", "aura").lower()
WAKE_WORD_ENGINE = os.getenv("WAKE_WORD_ENGINE", "aura_spotter")  # 'aura_spotter' or 'openwakeword'
OPENWAKEWORD_MODEL = os.getenv("OPENWAKEWORD_MODEL", "hey_jarvis")
WAKE_WORD_ENERGY_THRESHOLD = float(os.getenv("WAKE_WORD_ENERGY_THRESHOLD", "0.012"))

# Audio Capture & Silence Detection Configuration
INPUT_SAMPLE_RATE = 16000  # Native sample rate for Whisper and Wake-Word
SILENCE_ENERGY_THRESHOLD = float(os.getenv("SILENCE_ENERGY_THRESHOLD", "0.015"))
SILENCE_DURATION_SECONDS = float(os.getenv("SILENCE_DURATION_SECONDS", "0.9"))
MAX_RECORDING_DURATION = float(os.getenv("MAX_RECORDING_DURATION", "15.0"))
MIN_RECORDING_DURATION = float(os.getenv("MIN_RECORDING_DURATION", "0.5"))

# TTS Engine Selection ('edge' or 'piper')
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge").lower()

# Edge-TTS Neural Voice Configuration (Free, Humanized, Low-Latency)
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-AriaNeural")
EDGE_TTS_SAMPLE_RATE = 24000

# Piper TTS Configuration (Local Offline Fallback / Ultra-Fast Alternative)
ASSETS_DIR = BASE_DIR / "assets"
VOICES_DIR = ASSETS_DIR / "voices"
PIPER_MODEL_PATH = str(VOICES_DIR / "en_US-lessac-medium.onnx")
PIPER_CONFIG_PATH = str(VOICES_DIR / "en_US-lessac-medium.onnx.json")
PIPER_SAMPLE_RATE = 22050

# Audio Output Configuration (matches active TTS engine)
AUDIO_SAMPLE_RATE = EDGE_TTS_SAMPLE_RATE if TTS_ENGINE == "edge" else PIPER_SAMPLE_RATE

# Wikipedia Deep Search & Media Configuration
WIKIPEDIA_ENABLED_DEFAULT = os.getenv("WIKIPEDIA_ENABLED", "true").lower() == "true"
WIKIPEDIA_TIMEOUT = float(os.getenv("WIKIPEDIA_TIMEOUT", "6.0"))
WIKIPEDIA_MAX_ARTICLES = int(os.getenv("WIKIPEDIA_MAX_ARTICLES", "3"))
WIKIPEDIA_MAX_IMAGES = int(os.getenv("WIKIPEDIA_MAX_IMAGES", "6"))

# Conversational System Prompt for Voice
SYSTEM_PROMPT = (
    "You are AURA, an elegant, highly responsive desktop AI assistant with full visual and encyclopedic capabilities. "
    "You have direct access to Wikipedia knowledge, high-resolution photo galleries, desktop screen vision, and system tools. "
    "NEVER claim to be a text-only assistant or state that you cannot display images or access Wikipedia—the desktop interface displays cards and image galleries automatically. "
    "NEVER hallucinate or pretend to see an application running or claim to launch games or software unless explicit vision context is provided. Desktop apps and OS actions are executed natively by the system. "
    "Always provide direct, natural, and helpful spoken answers in 1 to 3 conversational sentences. "
    "Never use markdown bullet points, asterisks, citations, or raw markdown links, as your responses will be read aloud through text-to-speech."
)
