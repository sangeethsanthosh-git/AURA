from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

LANGUAGE_MODELS = {
    "en": "gemma3:1b",
    "ml": "qwen3:4b",
}

DEFAULT_LANGUAGE = "en"

WHISPER_MALAYALAM_CONFIDENCE = 0.80

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_THINK = False

LANGUAGE_VOICE_MODELS = {
    "en": BASE_DIR / "voices" / "en_US-lessac-medium.onnx",
    "ml": BASE_DIR / "voices" / "ml_IN-meera-medium.onnx",
}

PIPER_WINDOWS_PATH = BASE_DIR / "tools" / "piper" / "piper" / "piper.exe"
PIPER_LINUX_PATH = BASE_DIR / "tools" / "piper" / "piper" / "piper"
