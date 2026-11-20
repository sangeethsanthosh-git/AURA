"""
Phase 6 Prolonged Operation & End-to-End Streaming Latency Test.
Runs multiple consecutive STT -> Streaming Ollama -> Chunked Piper PCM cycles
while monitoring per-stage latency, Time-To-First-Audio (TTFA), process RAM, and RTX 2050 VRAM.
"""

from pathlib import Path
import sys
import os
import re
import time
import ctypes
import subprocess
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.stt_service import STTService
from backend.services.ollama_service import OllamaService
from backend.services.tts_service import TTSService


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def get_process_ram_mb() -> float:
    """Read current Windows process Working Set RSS in MB via kernel32.K32GetProcessMemoryInfo."""
    try:
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        k32.K32GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
            ctypes.c_ulong,
        ]
        k32.K32GetProcessMemoryInfo.restype = ctypes.c_bool
        handle = k32.GetCurrentProcess()
        if k32.K32GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize / (1024 * 1024)
    except Exception:
        pass
    return 0.0


def get_vram_used_mb() -> tuple[int, int]:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        used, total = [int(x.strip()) for x in out.split(",")]
        return used, total
    except Exception:
        return -1, -1


def run_prolonged_cycles(num_cycles: int = 8):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    sample_wav = PROJECT_ROOT / "assets" / "input_test.wav"
    if not sample_wav.exists():
        print(f"Error: sample WAV missing at {sample_wav}")
        sys.exit(1)

    print("=" * 72)
    print("       AURA VOICE V1 — PHASE 6 PROLONGED OPERATION & TTFA TEST")
    print("=" * 72)

    stt = STTService()
    ollama = OllamaService()
    tts = TTSService()

    t_load0 = time.perf_counter()
    stt.load_model()
    print(f"[Init] Whisper loaded (local cache, CPU INT8): {(time.perf_counter() - t_load0)*1000:.0f} ms")

    if not ollama.check_connection():
        print("[Error] Ollama server is offline. Please start `ollama serve`.")
        sys.exit(1)
    if not tts.is_ready():
        print("[Error] Piper TTS is not ready.")
        sys.exit(1)

    sentence_re = re.compile(r"[.!?]+(?=\s|\n|$)|\n+")
    prompts = [
        "Explain gravity briefly.",
        "What is the boiling point of water?",
        "Why is the ocean salty?",
        "Name one planet with rings.",
        "How does photosynthesis work?",
        "What is the speed of light?",
        "Why do seasons change?",
        "What causes thunder?",
    ]

    ram_start = get_process_ram_mb()
    vram_start, vram_total = get_vram_used_mb()
    print(f"[Baseline] Process RAM: {ram_start:.1f} MB | GPU VRAM: {vram_start}/{vram_total} MiB\n")

    ttfa_results = []
    stt_results = []

    for i in range(num_cycles):
        turn_start = time.perf_counter()

        # 1. STT
        t_stt = time.perf_counter()
        _transcribed = stt.transcribe(sample_wav)
        stt_ms = (time.perf_counter() - t_stt) * 1000
        stt_results.append(stt_ms)

        # 2. Streaming LLM -> First Sentence -> First PCM Audio Chunk
        t_llm = time.perf_counter()
        prompt = prompts[i % len(prompts)]
        buf = ""
        full_tokens = []
        ttft_ms = None
        first_audio_ms = None

        for tok in ollama.chat_stream([{"role": "user", "content": prompt}]):
            if ttft_ms is None:
                ttft_ms = (time.perf_counter() - t_llm) * 1000
            full_tokens.append(tok)
            buf += tok

            if first_audio_ms is None:
                match = sentence_re.search(buf)
                if match and match.end() >= 18:
                    first_sentence = buf[: match.end()].strip()
                    buf = buf[match.end() :].lstrip()
                    for chunk in tts.synthesize_pcm_stream(first_sentence):
                        if len(chunk) > 0:
                            first_audio_ms = (time.perf_counter() - turn_start) * 1000
                            break

        # If reply was short (<18 chars or single sentence without early split), synthesize now
        if first_audio_ms is None and buf.strip():
            for chunk in tts.synthesize_pcm_stream(buf.strip()):
                if len(chunk) > 0:
                    first_audio_ms = (time.perf_counter() - turn_start) * 1000
                    break

        total_ms = (time.perf_counter() - turn_start) * 1000
        ttfa_results.append(first_audio_ms or total_ms)

        ram_now = get_process_ram_mb()
        vram_now, _ = get_vram_used_mb()
        print(
            f"Cycle {i+1}/{num_cycles}: STT={stt_ms:4.0f}ms | TTFT={ttft_ms or 0:4.0f}ms | "
            f"TTFA={ttfa_results[-1]:4.0f}ms | Total={total_ms:4.0f}ms | "
            f"RAM={ram_now:5.1f}MB | VRAM={vram_now}/{vram_total}MiB"
        )

    ram_end = get_process_ram_mb()
    vram_end, _ = get_vram_used_mb()
    print("\n" + "-" * 72)
    print(f"Summary across {num_cycles} prolonged cycles:")
    print(f"  Avg STT Latency        : {np.mean(stt_results):.0f} ms")
    print(f"  Avg End-to-End TTFA    : {np.mean(ttfa_results):.0f} ms")
    print(f"  RAM Delta              : {ram_end - ram_start:+.1f} MB ({ram_start:.1f} -> {ram_end:.1f} MB)")
    print(f"  GPU VRAM Delta         : {vram_end - vram_start:+d} MiB ({vram_start} -> {vram_end}/{vram_total} MiB)")
    print("-" * 72)


if __name__ == "__main__":
    run_prolonged_cycles(num_cycles=8)
