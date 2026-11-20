"""
Phase 2 Verification Script: Microphone -> Faster-Whisper (STT) -> Ollama -> Piper TTS -> Speaker.
"""

from pathlib import Path
import sys
import time

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import OLLAMA_MODEL, WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE
from backend.services.ollama_service import OllamaService
from backend.services.tts_service import TTSService
from backend.services.audio_service import AudioService
from backend.services.stt_service import STTService


def run_phase2_test(audio_file_input: str | None = None) -> bool:
    print("=" * 60)
    print("      AURA VOICE V1 - PHASE 2 (SPEECH RECOGNITION)")
    print("=" * 60)

    # 1. Initialize services
    print("\n[Step 1/5] Initializing local services...")
    ollama = OllamaService()
    tts = TTSService()
    audio = AudioService()
    stt = STTService()

    # Pre-flight checks
    print(f"  Checking Ollama ({OLLAMA_MODEL})...", end=" ", flush=True)
    if not ollama.check_connection():
        print("FAILED! (Ollama server not running)")
        return False
    if not ollama.check_model_available():
        print(f"FAILED! (Model '{OLLAMA_MODEL}' not found)")
        return False
    print("READY")

    print("  Checking Piper TTS...", end=" ", flush=True)
    if not tts.is_ready():
        print("FAILED!")
        return False
    print("READY")

    print(
        f"  Loading Faster-Whisper STT ({WHISPER_MODEL_SIZE} on {WHISPER_DEVICE}/{WHISPER_COMPUTE_TYPE})...",
        end=" ",
        flush=True,
    )
    start_load = time.perf_counter()
    stt.load_model()
    print(f"READY ({time.perf_counter() - start_load:.2f}s)")

    # 2. Capture / load audio
    if audio_file_input and Path(audio_file_input).exists():
        print(f"\n[Step 2/5] Using test audio file: {audio_file_input}")
        recorded_audio = audio_file_input
    else:
        print("\n[Step 2/5] Live Microphone Capture:")
        print("  >> Please speak into your microphone now...")
        print("  >> AURA will automatically detect when you finish speaking.")

        def on_speech():
            print("  [Listening...] Speech detected! Recording...")

        start_rec = time.perf_counter()
        recorded_audio = audio.record_speech(
            timeout=8.0,
            on_speech_detected=on_speech,
        )
        rec_time = time.perf_counter() - start_rec

        if len(recorded_audio) == 0:
            print("  [Warning] No speech was detected within timeout.")
            return False

        duration = len(recorded_audio) / 16000
        print(f"  Recording finished. Captured {duration:.2f}s of speech in {rec_time:.2f}s.")

    # 3. Transcribe speech with Faster-Whisper
    print("\n[Step 3/5] Transcribing speech with Faster-Whisper...")
    start_stt = time.perf_counter()
    transcription = stt.transcribe(recorded_audio)
    stt_latency = time.perf_counter() - start_stt

    print(f"  Transcription: \"{transcription}\"")
    print(f"  STT Latency: {stt_latency:.2f} seconds")

    if not transcription.strip():
        print("  [Warning] Transcription was empty or unintelligible.")
        return False

    # 4. Generate AI response with Ollama
    print(f"\n[Step 4/5] Sending transcription to Ollama ({OLLAMA_MODEL})...")
    start_llm = time.perf_counter()
    response_text = ollama.generate_response(transcription)
    llm_latency = time.perf_counter() - start_llm

    print(f"  AURA Response: \"{response_text}\"")
    print(f"  LLM Latency: {llm_latency:.2f} seconds")

    # 5. Synthesize & play spoken output with Piper
    print("\n[Step 5/5] Synthesizing & speaking response with Piper TTS...")
    output_wav = PROJECT_ROOT / "assets" / "output_test.wav"
    start_tts = time.perf_counter()
    tts.synthesize(response_text, str(output_wav))
    tts_latency = time.perf_counter() - start_tts
    print(f"  TTS Latency: {tts_latency:.2f} seconds")

    print("  Playing response through speakers...")
    audio.play_wav(str(output_wav), block=True)

    print("\n" + "=" * 60)
    print("PHASE 2 SUMMARY & BENCHMARK:")
    print(f"  - STT Transcription: {stt_latency:.2f}s")
    print(f"  - LLM Inference:     {llm_latency:.2f}s")
    print(f"  - TTS Synthesis:     {tts_latency:.2f}s")
    print(f"  - Pipeline Latency:  {stt_latency + llm_latency + tts_latency:.2f}s (before playback)")
    print("=" * 60)
    print("PHASE 2 SPEECH RECOGNITION PIPELINE VERIFIED SUCCESSFULLY!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    audio_arg = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_phase2_test(audio_arg)
    sys.exit(0 if success else 1)
