"""Local benchmark scaffolding for future ASR/TTS model comparisons."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpeechBenchmarkSample:
    sample_id: str
    language: str
    text: str
    category: str


ASR_EVALUATION_SET: tuple[SpeechBenchmarkSample, ...] = (
    SpeechBenchmarkSample("asr-en-action", "en", "Open Chrome and search for Python tutorials.", "intent_preservation"),
    SpeechBenchmarkSample("asr-ml-weather", "ml", "എനിക്ക് ഇന്ന് കാലാവസ്ഥ അറിയണം.", "malayalam"),
    SpeechBenchmarkSample("asr-manglish-weather", "mixed", "njan innu Kochi-il aanu, weather engane undu?", "manglish"),
    SpeechBenchmarkSample("asr-mixed-code", "mixed", "ee Python code onn explain cheyyamo?", "code_switching"),
    SpeechBenchmarkSample("asr-manglish-rag", "mixed", "RAG use cheythu local knowledge retrieve cheyyan pattumo?", "technical_manglish"),
)

TTS_EVALUATION_SET: tuple[SpeechBenchmarkSample, ...] = (
    SpeechBenchmarkSample("tts-en-greeting", "en", "Hello. How can I help you?", "naturalness"),
    SpeechBenchmarkSample("tts-en-action", "en", "Open Chrome and search for the latest AI news.", "desktop_action"),
    SpeechBenchmarkSample("tts-ml-casual", "ml", "എങ്ങനെയുണ്ട്? ഇന്ന് എന്താ പരിപാടി?", "malayalam_conversational"),
    SpeechBenchmarkSample("tts-manglish", "mixed", "entha cheyyunne? njan ivide undu.", "manglish"),
    SpeechBenchmarkSample("tts-mixed-weather", "mixed", "ഇന്ന് weather നല്ലതാണ്, so namukku പുറത്തേക്ക് പോകാം.", "code_switching"),
)


def benchmark_plan() -> dict[str, object]:
    return {
        "asr_candidates": ["faster-whisper", "jona276/whisper-small-manglish"],
        "tts_candidates": ["piper", "ai4bharat/IndicF5", "ai4bharat/indic-parler-tts"],
        "metrics": [
            "intent_preservation",
            "entity_preservation",
            "WER",
            "CER where useful",
            "latency",
            "model_load_time",
            "CPU/RAM/VRAM usage",
            "pronunciation",
            "naturalness",
        ],
        "asr_samples": [sample.__dict__ for sample in ASR_EVALUATION_SET],
        "tts_samples": [sample.__dict__ for sample in TTS_EVALUATION_SET],
        "note": "Candidate models are not auto-installed. Run benchmarks before enabling a non-Piper engine.",
    }
