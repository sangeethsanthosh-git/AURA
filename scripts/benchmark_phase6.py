"""
Phase 6 Hardware & Latency Benchmark Script for AURA Voice V1.
Measures Faster-Whisper (CPU vs CUDA), Ollama (Full vs Streaming TTFS), Piper TTS,
and GPU VRAM usage on the target RTX 2050 (4 GB VRAM) laptop.
"""

from pathlib import Path
import sys
import time
import json
import subprocess
import requests
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_CONTEXT_LENGTH,
    SYSTEM_PROMPT,
    WHISPER_MODEL_SIZE,
    PIPER_MODEL_PATH,
    PIPER_CONFIG_PATH,
    AUDIO_SAMPLE_RATE,
)
from backend.services.tts_service import TTSService


def get_vram_mb() -> dict:
    """Query nvidia-smi for total, used, and free VRAM in MiB."""
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,memory.free",
                "--format=csv,noheader,nounits",
            ],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        name, total, used, free = [x.strip() for x in out.split(",")]
        return {
            "gpu": name,
            "total_mb": int(total),
            "used_mb": int(used),
            "free_mb": int(free),
        }
    except Exception as e:
        return {"error": str(e)}


def benchmark_whisper(audio_path: Path):
    print("\n" + "=" * 65)
    print("1. FASTER-WHISPER BENCHMARK (CPU INT8 vs CUDA GPU)")
    print("=" * 65)
    if not audio_path.exists():
        print(f"[SKIP] Audio file not found: {audio_path}")
        return

    from faster_whisper import WhisperModel
    import soundfile as sf

    audio_data, sr = sf.read(str(audio_path), dtype="float32")
    if audio_data.ndim > 1:
        audio_data = audio_data.flatten()
    duration_sec = len(audio_data) / sr
    print(f"Sample audio: {audio_path.name} ({duration_sec:.2f}s @ {sr}Hz)")

    configs = [
        {"name": "CPU INT8 (beam=5, default threads)", "device": "cpu", "compute_type": "int8", "beam": 5, "threads": 0},
        {"name": "CPU INT8 (beam=1, threads=4)", "device": "cpu", "compute_type": "int8", "beam": 1, "threads": 4},
        {"name": "CPU INT8 (beam=1, threads=6)", "device": "cpu", "compute_type": "int8", "beam": 1, "threads": 6},
        {"name": "CUDA float16 (beam=1)", "device": "cuda", "compute_type": "float16", "beam": 1, "threads": 0},
    ]

    for cfg in configs:
        vram_before = get_vram_mb()
        try:
            t0 = time.perf_counter()
            model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=cfg["device"],
                compute_type=cfg["compute_type"],
                cpu_threads=cfg["threads"],
                local_files_only=True,
            )
            load_ms = (time.perf_counter() - t0) * 1000

            # Warmup run + timed run
            for run_idx in range(2):
                t1 = time.perf_counter()
                segments, _ = model.transcribe(
                    audio_data,
                    language="en",
                    beam_size=cfg["beam"],
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500),
                )
                text = " ".join(s.text.strip() for s in segments).strip()
                infer_ms = (time.perf_counter() - t1) * 1000

            vram_after = get_vram_mb()
            vram_delta = vram_after.get("used_mb", 0) - vram_before.get("used_mb", 0)
            print(
                f"  - {cfg['name']}:\n"
                f"      Load: {load_ms:.0f} ms | Inference (warm): {infer_ms:.0f} ms | "
                f"VRAM delta: {vram_delta:+d} MiB (Free: {vram_after.get('free_mb')} MiB)\n"
                f"      Text: \"{text}\""
            )
            del model
        except Exception as e:
            print(f"  - {cfg['name']}: UNAVAILABLE / FAILED -> {e}")


def benchmark_ollama():
    print("\n" + "=" * 65)
    print("2. OLLAMA BENCHMARK (Non-Streaming vs Streaming TTFS)")
    print("=" * 65)
    prompt = "Explain why the sky is blue in two short sentences."
    url = f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    # Warmup / Non-streaming
    vram_before = get_vram_mb()
    t0 = time.perf_counter()
    res = requests.post(
        url,
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": OLLAMA_CONTEXT_LENGTH, "temperature": 0.7},
        },
        timeout=30.0,
    )
    res.raise_for_status()
    full_ms = (time.perf_counter() - t0) * 1000
    full_reply = res.json()["message"]["content"].strip()
    vram_after = get_vram_mb()
    print(f"  - Model: {OLLAMA_MODEL} | GPU Used VRAM: {vram_after.get('used_mb')} / {vram_after.get('total_mb')} MiB")
    print(f"  - Full Non-Streaming Response: {full_ms:.0f} ms")
    print(f"    Reply: \"{full_reply}\"")

    # Streaming: Measure TTFT and Time-To-First-Sentence (TTFS)
    t0 = time.perf_counter()
    ttft_ms = None
    ttfs_ms = None
    first_sentence = ""
    accumulated = ""
    with requests.post(
        url,
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": True,
            "options": {"num_ctx": OLLAMA_CONTEXT_LENGTH, "temperature": 0.7},
        },
        stream=True,
        timeout=30.0,
    ) as stream_res:
        stream_res.raise_for_status()
        for line in stream_res.iter_lines(decode_unicode=True):
            if not line:
                continue
            chunk = json.loads(line)
            token = chunk.get("message", {}).get("content", "")
            if token:
                if ttft_ms is None:
                    ttft_ms = (time.perf_counter() - t0) * 1000
                accumulated += token
                if ttfs_ms is None and any(p in accumulated for p in (". ", "! ", "? ", ".\n", "!\n", "?\n")):
                    ttfs_ms = (time.perf_counter() - t0) * 1000
                    first_sentence = accumulated.strip()
            if chunk.get("done"):
                break
    stream_total_ms = (time.perf_counter() - t0) * 1000
    print(f"  - Streaming TTFT (first token): {ttft_ms:.0f} ms")
    print(f"  - Streaming TTFS (first sentence ready for TTS): {ttfs_ms or stream_total_ms:.0f} ms")
    print(f"  - Streaming Total Generation: {stream_total_ms:.0f} ms")
    if first_sentence:
        print(f"    First sentence: \"{first_sentence}\"")


def benchmark_piper():
    print("\n" + "=" * 65)
    print("3. PIPER TTS BENCHMARK (WAV Disk I/O vs Raw PCM Memory Stream)")
    print("=" * 65)
    tts = TTSService()
    if not tts.is_ready():
        print("[SKIP] Piper TTS not ready.")
        return

    sample_sentence = "The sky appears blue because Earth's atmosphere scatters shorter blue wavelengths of sunlight."
    out_wav = PROJECT_ROOT / "assets" / "benchmark_tts.wav"

    # Method A: Current WAV file write
    t0 = time.perf_counter()
    tts.synthesize(sample_sentence, str(out_wav))
    wav_ms = (time.perf_counter() - t0) * 1000
    if out_wav.exists():
        out_wav.unlink()
    print(f"  - File WAV synthesis (`--output_file`): {wav_ms:.0f} ms")

    # Method B: Direct `--output_raw` memory stdout PCM
    cmd = [
        tts.piper_binary,
        "--model",
        str(Path(PIPER_MODEL_PATH).resolve()),
        "--output_raw",
        "--quiet",
    ]
    if Path(PIPER_CONFIG_PATH).exists():
        cmd.extend(["--config", str(Path(PIPER_CONFIG_PATH).resolve())])

    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        input=sample_sentence.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    raw_ms = (time.perf_counter() - t0) * 1000
    pcm_samples = np.frombuffer(proc.stdout, dtype=np.int16)
    audio_dur = len(pcm_samples) / AUDIO_SAMPLE_RATE
    print(
        f"  - Raw PCM memory synthesis (`--output_raw`): {raw_ms:.0f} ms "
        f"(Audio length: {audio_dur:.2f}s)"
    )


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    print("=" * 65)
    print("          AURA VOICE V1 — PHASE 6 BENCHMARK")
    print("=" * 65)
    print(f"Initial GPU State: {get_vram_mb()}")

    benchmark_whisper(PROJECT_ROOT / "assets" / "input_test.wav")
    benchmark_ollama()
    benchmark_piper()
    print("\nBenchmark complete.")


if __name__ == "__main__":
    main()
