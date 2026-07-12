import logging
import os
import platform
import sys
from shutil import which

from conversation_manager import ConversationManager
from language_manager import LanguageManager
from model_router import ModelRouter
from tts_manager import TTSManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger(__name__)


def configure_console_encoding() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def print_header() -> None:
    os.system("cls" if platform.system() == "Windows" else "clear")
    print()
    print("+" + "-" * 48 + "+")
    print("|" + "AURA Assistant".center(48) + "|")
    print("|" + "Local multilingual AI companion".center(48) + "|")
    print("+" + "-" * 48 + "+")
    print("Type exit, quit, or bye to close.")
    print("Try: Speak in Malayalam")
    print("Try: Switch back to English\n")


def print_message(name: str, message: str) -> None:
    print(f"{name}:")
    print(f"  {message}\n")


def check_requirements(tts_manager: TTSManager) -> bool:
    missing = tts_manager.check_requirements()

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


def main() -> None:
    configure_console_encoding()

    language_manager = LanguageManager()
    model_router = ModelRouter()
    conversation_manager = ConversationManager(language_manager, model_router)
    tts_manager = TTSManager()

    if not check_requirements(tts_manager):
        return

    print_header()

    greeting = (
        "Hello Sangeeth. I am Aura, your personal AI assistant. "
        "How can I help you today?"
    )

    print_message("Aura", greeting)
    tts_manager.speak(greeting, language_manager.current_language)

    while True:
        user_input = input("You > ").strip()

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", "bye"}:
            goodbye = "Goodbye Sangeeth. Have a wonderful day."
            print()
            print_message("Aura", goodbye)
            tts_manager.speak(goodbye, language_manager.current_language)
            break

        print("\nAura is thinking...\n")

        try:
            response, selection = conversation_manager.ask(user_input)
        except RuntimeError as exc:
            LOGGER.exception("AURA failed to answer.")
            print_message("Aura", f"Sorry, something went wrong: {exc}")
            continue

        visible_language = language_manager.state.name
        print(f"Language: {visible_language} | Model: {selection.model}\n")
        print_message("Aura", response)
        tts_manager.speak(response, language_manager.current_language)


if __name__ == "__main__":
    main()
