"""
Phase 1 Prototype Verification Script for AURA Voice Assistant.
Pipeline: Text Input -> Ollama (qwen3:1.7b) -> Piper TTS -> Speaker.
"""

import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import OLLAMA_MODEL, PIPER_MODEL_PATH
from backend.services.ollama_service import OllamaService
from backend.services.tts_service import TTSService
from backend.services.audio_service import AudioService


def run_phase1_test(test_prompt: str = "Hello AURA, can you hear me? Please introduce yourself in one short sentence."):
    print("=" * 60)
    print("      AURA VOICE V1 - PHASE 1 PROTOTYPE TEST")
    print("=" * 60)

    # 1. Initialize services
    print("\n[Step 1/5] Initializing local services...")
    ollama = OllamaService()
    tts = TTSService()
    audio = AudioService()

    # 2. Check Ollama Connection
    print("  Checking Ollama server connection...", end=" ", flush=True)
    if not ollama.check_connection():
        print("FAILED!")
        print("  [Error] Ollama is not responding on http://localhost:11434.")
        print("  Please make sure Ollama is running (`ollama serve`).")
        return False
    print("OK")

    # 3. Check Model Availability
    print(f"  Checking Ollama model '{OLLAMA_MODEL}'...", end=" ", flush=True)
    if not ollama.check_model_available():
        print("NOT FOUND!")
        print(f"  [Warning] Model '{OLLAMA_MODEL}' is not ready yet in Ollama.")
        return False
    print("READY")

    # 4. Check TTS Engine
    print(f"  Checking Piper TTS engine and voice model...", end=" ", flush=True)
    if not tts.is_ready():
        print("FAILED!")
        print(f"  [Error] Voice model missing at: {PIPER_MODEL_PATH}")
        return False
    print("READY")

    # 5. Generate AI Response
    print("\n[Step 2/5] Generating LLM response from Ollama...")
    print(f"  Prompt: \"{test_prompt}\"")

    start_llm = time.perf_counter()
    response_text = ollama.generate_response(test_prompt)
    llm_latency = time.perf_counter() - start_llm

    print(f"  Response: \"{response_text}\"")
    print(f"  LLM Latency: {llm_latency:.2f} seconds")

    if not response_text:
        print("  [Error] Received empty response from Ollama.")
        return False

    # 6. Synthesize Speech with Piper
    print("\n[Step 3/5] Synthesizing speech with Piper TTS...")
    output_wav = PROJECT_ROOT / "assets" / "output_test.wav"

    start_tts = time.perf_counter()
    tts.synthesize(response_text, str(output_wav))
    tts_latency = time.perf_counter() - start_tts

    print(f"  Generated audio: {output_wav}")
    print(f"  TTS Latency: {tts_latency:.2f} seconds")

    # 7. Play Audio via Speaker
    print("\n[Step 4/5] Playing audio through speaker...")
    start_playback = time.perf_counter()
    audio.play_wav(str(output_wav), block=True)
    playback_duration = time.perf_counter() - start_playback
    print(f"  Playback completed in {playback_duration:.2f} seconds.")

    # 8. Summary
    print("\n[Step 5/5] Performance Summary:")
    print(f"  - LLM Inference:   {llm_latency:.2f}s")
    print(f"  - TTS Synthesis:   {tts_latency:.2f}s")
    print(f"  - Total Pipeline:  {llm_latency + tts_latency:.2f}s (before playback)")
    print("=" * 60)
    print("PHASE 1 VERIFICATION SUCCESSFUL: Text -> LLM -> TTS -> Audio playback.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Hello AURA, can you hear me? Please introduce yourself in one short sentence."
    success = run_phase1_test(prompt)
    sys.exit(0 if success else 1)
