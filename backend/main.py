"""
AURA Voice Assistant - Main Entry Point.
Launches the AURA Backend & opens the animated Voice Orb UI (Desktop Electron or Browser).
"""

from pathlib import Path
import os
import sys
import time
import shutil
import socket
import subprocess
import webbrowser
import logging
import threading

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import OLLAMA_MODEL, WHISPER_MODEL_SIZE, WAKE_WORD_PHRASE
from backend.services.ollama_service import OllamaService
from backend.services.tts_service import TTSService
from backend.services.audio_service import AudioService
from backend.services.stt_service import STTService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("AURA")


def _find_ollama_exe() -> str | None:
    """Locate the Ollama executable on Windows."""
    on_path = shutil.which("ollama")
    if on_path:
        return on_path
    default_win = Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"))
    if default_win.exists():
        return str(default_win)
    return None


def ensure_ollama_running(ollama: OllamaService) -> bool:
    """Check if Ollama is running; attempt to start `ollama serve` if installed."""
    if ollama.check_connection():
        return True

    ollama_exe = _find_ollama_exe()
    if not ollama_exe:
        return False

    print("STARTING...", end=" ", flush=True)
    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        startupinfo = None
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
        subprocess.Popen(
            [ollama_exe, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            startupinfo=startupinfo,
        )
        for _ in range(12):
            time.sleep(0.5)
            if ollama.check_connection():
                return True
    except Exception as e:
        logger.warning(f"Failed to auto-start Ollama: {e}")

    return False


def _wait_for_port(host: str, port: int, timeout: float = 20.0) -> bool:
    """Wait until FastAPI server port is listening."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def run_cli_mode():
    """Terminal voice and text interactive loop (CLI fallback)."""
    ollama = OllamaService()
    tts = TTSService()
    audio = AudioService()
    stt = STTService()

    print(f"  Pre-warming Faster-Whisper ({WHISPER_MODEL_SIZE})...", end=" ", flush=True)
    stt.load_model()
    print("READY")

    print("\n--- AURA Terminal Mode Active ---")
    print("  [ENTER]      : Talk through microphone")
    print("  Type text    : Send manual text prompt")
    print("  'q' / 'exit' : Quit\n")

    while True:
        try:
            choice = input("Press [ENTER] to talk or type a prompt: ").strip()
            if choice.lower() in ("exit", "quit", "q"):
                print("Exiting AURA. Goodbye!")
                break

            if choice == "":
                print("\n[Listening...] Speak now...")
                recorded_data = audio.record_speech(timeout=7.0)
                if len(recorded_data) == 0:
                    print("  [!] No speech detected.\n")
                    continue
                user_text = stt.transcribe(recorded_data)
                if not user_text.strip():
                    print("  [!] Could not understand speech.\n")
                    continue
                print(f"You (Voice): \"{user_text}\"")
                prompt_to_send = user_text
            else:
                prompt_to_send = choice

            print(f"\n[Thinking...] Querying {OLLAMA_MODEL}...")
            reply = ollama.generate_response(prompt_to_send)
            print(f"AURA: {reply}")

            output_wav = PROJECT_ROOT / "assets" / "output_test.wav"
            tts.synthesize(reply, str(output_wav))
            audio.play_wav(str(output_wav), block=True)
            print()

        except (KeyboardInterrupt, EOFError):
            print("\nExiting AURA.")
            break


def main():
    print("=" * 60)
    print("          AURA VOICE ASSISTANT V1")
    print("=" * 60)

    ollama = OllamaService()
    tts = TTSService()

    print(f"  Checking Ollama server ({OLLAMA_MODEL})...", end=" ", flush=True)
    if ensure_ollama_running(ollama):
        print("READY")
    else:
        print("WARNING (Ollama not running yet; start `ollama serve` before speaking)")

    print("  Checking Piper TTS...", end=" ", flush=True)
    if not tts.is_ready():
        print("FAILED!")
        return
    print("READY")

    print(f"  Wake-Word Configured: \"{WAKE_WORD_PHRASE}\" (Loopback Protected)")
    print("=" * 60)

    # CLI mode if explicitly requested
    if "--cli" in sys.argv:
        run_cli_mode()
        return

    # Graphical UI Mode (Electron Desktop App by default, or Browser via --browser)
    use_browser = "--browser" in sys.argv
    electron_exe = PROJECT_ROOT / "frontend" / "node_modules" / "electron" / "dist" / "electron.exe"
    electron_main = PROJECT_ROOT / "frontend" / "electron" / "main.cjs"
    ui_url = "http://127.0.0.1:8000"

    import uvicorn

    config = uvicorn.Config("backend.api.app:app", host="127.0.0.1", port=8000, reload=False, log_level="info")
    server = uvicorn.Server(config)

    def _launch_ui():
        if not _wait_for_port("127.0.0.1", 8000, timeout=30.0):
            logger.error("Backend server did not start in time.")
            return

        if not use_browser and electron_exe.exists() and electron_main.exists():
            print(f"\n[*] Launching AURA Desktop Window (Electron)...")
            print(f"[*] Web UI also accessible at: {ui_url}\n")
            try:
                proc = subprocess.Popen(
                    [str(electron_exe), str(electron_main)],
                    cwd=str(PROJECT_ROOT / "frontend"),
                )
                proc.wait()
                # Close server cleanly when user closes the Electron window
                server.should_exit = True
                return
            except Exception as e:
                logger.warning(f"Could not launch Electron window ({e}), falling back to browser.")

        print(f"\n[*] Launching AURA Voice Orb UI in browser: {ui_url}\n")
        webbrowser.open(ui_url)

    print("\n[*] Starting AURA Backend Server (loading Faster-Whisper on CPU)...")
    print("    Modes: default (Desktop UI) | `--browser` (Web UI) | `--cli` (Terminal)\n")

    threading.Thread(target=_launch_ui, daemon=True).start()
    server.run()


if __name__ == "__main__":
    main()
