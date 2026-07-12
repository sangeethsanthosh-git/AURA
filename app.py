import subprocess
import re
import os
import platform
from pathlib import Path
from shutil import which

# ----------------------------
# Configuration
# ----------------------------
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
VOICE_MODEL = BASE_DIR / "voices" / "en_US-lessac-medium.onnx"
OLLAMA_MODEL = "gemma3:1b"

if platform.system() == "Windows":
    PIPER_PATH = BASE_DIR / "tools" / "piper" / "piper" / "piper.exe"
else:
    PIPER_PATH = BASE_DIR / "tools" / "piper" / "piper" / "piper"

# ----------------------------
# Clean text for Piper
# ----------------------------

def clean_text(text):
    # Remove ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)

    # Remove artifacts like 3DK, 5DK, 12DK
    text = re.sub(r'\b\d+DK\b', '', text)

    # Remove markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)

    # Remove emojis and unsupported symbols
    text = re.sub(r'[^\w\s.,!?;:\'()\-]', '', text)

    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def print_header():
    os.system("cls" if platform.system() == "Windows" else "clear")
    print()
    print("+" + "-" * 48 + "+")
    print("|" + "AURA Assistant".center(48) + "|")
    print("|" + "Local AI voice companion".center(48) + "|")
    print("+" + "-" * 48 + "+")
    print("Type exit, quit, or bye to close.\n")


def print_message(name, message):
    print(f"{name}:")
    print(f"  {message}\n")


def play_audio(audio_file):
    if platform.system() == "Windows":
        import winsound

        winsound.PlaySound(str(audio_file), winsound.SND_FILENAME)
        return

    player = "aplay" if which("aplay") else "paplay"
    subprocess.run([player, str(audio_file)], check=True)


def check_requirements():
    missing = []

    if not PIPER_PATH.exists():
        missing.append(f"Piper was not found at {PIPER_PATH}")

    if not VOICE_MODEL.exists():
        missing.append(f"Voice model was not found at {VOICE_MODEL}")

    if which("ollama") is None:
        missing.append("Ollama was not found. Install Ollama and make sure it is in PATH.")

    if missing:
        print_header()
        print("Setup needed:\n")
        for item in missing:
            print(f"- {item}")
        print()
        return False

    return True


# ----------------------------
# Text-to-Speech (Piper)
# ----------------------------
def speak(text):
    if not text:
        return

    OUTPUT_DIR.mkdir(exist_ok=True)
    outfile = OUTPUT_DIR / "speech.wav"

    if outfile.exists():
        outfile.unlink()

    subprocess.run(
        [
            str(PIPER_PATH),
            "--model",
            str(VOICE_MODEL),
            "--output_file",
            str(outfile)
        ],
        input=text,
        text=True,
        check=True
    )

    play_audio(outfile)

# ----------------------------
# Ollama
# ----------------------------
def ask_ollama(prompt):
    system = (
        "You are Aura, a desktop voice assistant. "
        "Answer in 2 or 3 short sentences. "
        "Do not use markdown, emojis, bullet points, or special symbols."
    )

    full_prompt = f"{system}\n\nUser: {prompt}\nAssistant:"

    result = subprocess.run(
        ["ollama", "run", OLLAMA_MODEL],
        input=full_prompt,
        capture_output=True,
        text=True
    )

    return result.stdout.strip()

# ----------------------------
# Main
# ----------------------------
def main():
    if not check_requirements():
        return

    print_header()

    greeting = (
        "Hello Sangeeth. "
        "I am Aura, your personal AI assistant. "
        "How can I help you today?"
    )

    print_message("Aura", greeting)
    speak(greeting)

    while True:

        user_input = input("You > ").strip()

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "bye"]:

            goodbye = "Goodbye Sangeeth. Have a wonderful day."

            print()
            print_message("Aura", goodbye)
            speak(goodbye)
            break

        print("\nAura is thinking...\n")
        response = ask_ollama(user_input)

        response = clean_text(response)

        print_message("Aura", response)

        speak(response)

if __name__ == "__main__":
    main()
