import logging
import os
import platform
import sys
from dataclasses import dataclass
from typing import Any
from shutil import which
from backend.voice_studio.normalization import SpeechNormalizer

from backend.router.service_manager import ServiceManager
from backend.router.smart_router import SmartRouter
from backend.voice.manager import VoiceInputManager
from conversation_manager import ConversationManager
from language_manager import LanguageManager
from model_router import ModelRouter
from tts_manager import TTSManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AssistantOutput:
    """Presentation model that keeps metadata separate from speakable text.

    The CLI prints both fields, while Piper receives only ``assistant_message``.
    Future desktop UI code can use the same split to render metadata in an
    info panel without risking metadata leakage into TTS.
    """

    metadata: dict[str, str]
    assistant_message: str
    spoken_text: str | None = None


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
    print("Commands: /chat, /weather Kochi, /wiki Alan Turing, /nvidia hello")
    print("Commands: /hf explain transformers, /map Kochi")
    print("Commands: /file C:\\path\\doc.pdf, /knowledge add C:\\path\\notes.md")
    print("Commands: /voice, /screen")
    print("Try: Speak in Malayalam")
    print("Try: Switch back to English\n")


def print_message(name: str, message: str) -> None:
    print(f"{name}:")
    print(f"  {message}\n")


def print_assistant_output(name: str, output: AssistantOutput) -> None:
    """Print metadata for display and the assistant message as separate blocks."""
    print()
    for key in ("Language", "Provider", "Model", "Source"):
        print(f"{key} : {output.metadata.get(key, 'Unknown')}")
    print()
    print(f"{name}:")
    print()
    print(output.assistant_message)
    print()


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


def build_assistant_output(response: dict[str, Any]) -> AssistantOutput:
    """Convert a structured service response into display and speech parts."""
    route = response.get("route", {})
    metadata = {
        "Language": str(route.get("language", "English")),
        "Provider": str(route.get("provider", response.get("provider", "Unknown"))),
        "Model": str(route.get("model", "None")),
        "Source": str(route.get("source", "Unknown")),
    }

    normalizer = SpeechNormalizer()

    if not response.get("ok"):
        error = response.get("error") or {}
        message = f"Sorry, {error.get('message', 'the service request failed.')}"
        return AssistantOutput(
            metadata=metadata,
            assistant_message=message,
            spoken_text=normalizer.normalize(message, str(route.get("language", "en")).lower()[:2]),
        )

    data = response.get("data", {})
    provider = response.get("provider")
    action = response.get("action")
    body = ""

    if response.get("message"):
        body = str(response["message"])
    elif provider == "weather" and action == "current_weather":
        location = data.get("location", {})
        current = data.get("current_weather", {})
        body = (
            f"{location.get('name', 'Selected location')}: "
            f"{current.get('temperature')} deg C, wind {current.get('windspeed')} km/h."
        )
    elif provider == "maps" and action == "search_location":
        results = data.get("results", [])
        if not results:
            body = "No matching locations found."
        else:
            body = "\n".join(
            f"{index}. {item.get('display_name')} ({item.get('latitude')}, {item.get('longitude')})"
            for index, item in enumerate(results[:5], start=1)
            )
    elif provider == "wikipedia" and action == "search":
        results = data.get("results", [])
        body = "\n".join(f"- {item.get('title')}" for item in results) or "No Wikipedia results found."
    elif provider == "web":
        body = str(response.get("message") or "")
    elif provider == "knowledge":
        body = str(response.get("message") or "")
        sources = data.get("sources") if isinstance(data, dict) else None
        if sources:
            source_lines = []
            for source in sources[:5]:
                filename = source.get("filename", "Unknown source")
                section = source.get("section")
                source_lines.append(f"- {filename}" + (f" / {section}" if section else ""))
            body = body.rstrip() + "\n\nSources:\n" + "\n".join(source_lines)
    elif "content" in data:
        body = str(data["content"])
    else:
        body = str(data)

    return AssistantOutput(
        metadata=metadata,
        assistant_message=body,
        spoken_text=normalizer.normalize(body, str(route.get("language", "en")).lower()[:2]),
    )


def normalize_cli_command(command: str) -> tuple[str, str] | None:
    """Route slash commands to the service manager.

    Plain text input intentionally returns ``None`` so the original Ollama
    conversation path remains unchanged for the default workflow.
    """
    if not command.startswith("/"):
        return None

    name, _, argument = command.partition(" ")
    argument = argument.strip()

    if name == "/chat":
        if not argument:
            return "Aura", "Usage: /chat your message"
        return "Aura", argument

    if name == "/weather":
        if not argument:
            return "Weather", "Current weather"
        return "Weather", f"What is the weather in {argument}?"

    if name == "/wiki":
        if not argument:
            return "Wikipedia", "Usage: /wiki Alan Turing"
        return "Wikipedia", f"/wiki {argument}"

    if name in {"/groq", "/grok"}:
        if not argument:
            return "Groq", f"Usage: {name} hello"
        return "Groq", f"{name} {argument}"

    if name in {"/nvidia", "/nim"}:
        if not argument:
            return "NVIDIA", f"Usage: {name} design an agent coding strategy"
        return "NVIDIA", f"{name} {argument}"

    if name == "/hf":
        if not argument:
            return "Hugging Face", "Usage: /hf explain transformers"
        return "Hugging Face", f"/hf {argument}"

    if name == "/hug":
        if not argument:
            return "Hugging Face", "Usage: /hug explain transformers"
        return "Hugging Face", f"/hug {argument}"

    if name == "/ollama":
        if not argument:
            return "Ollama", "Usage: /ollama optional-model your message"
        return "Ollama", f"/ollama {argument}"

    if name == "/web":
        if not argument:
            return "Web", "Usage: /web current topic"
        return "Web", f"/web {argument}"

    if name == "/map":
        if not argument:
            return "Maps", "Usage: /map Kochi"
        return "Maps", f"Locate {argument}"

    if name == "/file":
        if not argument:
            return "Knowledge", "Usage: /file C:\\path\\document.pdf"
        return "Knowledge", f"Analyze file {argument}"

    if name == "/knowledge":
        if not argument:
            return "Knowledge", "Usage: /knowledge add C:\\path\\notes.md OR /knowledge search query"
        verb, _, rest = argument.partition(" ")
        if verb.lower() in {"add", "import", "remember"} and rest.strip():
            return "Knowledge", f"Add {rest.strip()} to my knowledge base"
        if verb.lower() in {"remove", "delete"} and rest.strip():
            return "Knowledge", f"Remove document {rest.strip()} from knowledge base"
        if verb.lower() in {"list", "show"}:
            return "Knowledge", "List knowledge documents"
        query = rest.strip() if verb.lower() == "search" and rest.strip() else argument
        return "Knowledge", f"Search my knowledge for {query}"

    if name == "/screen":
        lowered = argument.lower()
        if lowered in {"text", "read", "ocr"}:
            return "Aura", "Read the text on my screen."
        if lowered in {"describe", "description"}:
            return "Aura", "What do you see on my screen?"
        if lowered in {"app", "application", "window"}:
            return "Aura", "What application is currently open?"
        if lowered == "verify":
            return "Aura", "Verify the current screen state."
        return "Aura", argument or "Look at my screen."

    return "Aura", f"Unknown command: {name}"


def capture_voice_cli(voice_manager: VoiceInputManager) -> str | None:
    result = voice_manager.start_recording()
    if not result.success:
        print_message("Voice", result.error or "Voice input could not start.")
        return None

    print_message("Voice", "Listening. Press Enter to stop recording.")
    input()
    result = voice_manager.stop_and_transcribe()
    if not result.success:
        print_message("Voice", result.error or "I could not transcribe that recording.")
        return None

    print_message("Voice transcript", result.text)
    return result.text.strip() or None


def main() -> None:
    configure_console_encoding()

    language_manager = LanguageManager()
    model_router = ModelRouter()
    conversation_manager = ConversationManager(language_manager, model_router)
    service_manager = ServiceManager(conversation_manager)
    smart_router = SmartRouter(service_manager)
    tts_manager = TTSManager()
    voice_manager = VoiceInputManager()

    if not check_requirements(tts_manager):
        return

    print_header()

    greeting = (
        "Hello . I am Aura, a personal AI assistant. "
        "How can I help you today?"
    )

    print_message("Aura", greeting)
    tts_manager.speak(greeting, language_manager.current_language)

    while True:
        user_input = input("You > ").strip()

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", "bye"}:
            goodbye = "Goodbye  . Have a wonderful day."
            print()
            print_message("Aura", goodbye)
            tts_manager.speak(goodbye, language_manager.current_language)
            break

        if user_input.lower() == "/voice":
            transcript = capture_voice_cli(voice_manager)
            if not transcript:
                continue
            user_input = transcript

        command_response = normalize_cli_command(user_input)
        if command_response is not None:
            name, routed_input = command_response
            if routed_input.startswith("Usage:") or routed_input.startswith("Unknown command:"):
                print()
                print_message(name, routed_input)
                continue
            if user_input.lower().startswith("/screen"):
                print_message("Aura", "AURA is looking at your screen...")
            if any(term in routed_input.lower() for term in ("latest", "recent", "currently", "current version", "today", "news")):
                print_message("Aura", "Searching the web if current information is needed...")
            response = smart_router.ask(routed_input)
            output = build_assistant_output(response)
            print_assistant_output(name, output)
            if name == "Aura":
                tts_manager.speak(output.spoken_text or output.assistant_message, language_manager.current_language)
            continue

        print("\nAura is thinking...\n")

        try:
            routed_response = smart_router.ask(user_input)
        except RuntimeError as exc:
            LOGGER.exception("AURA failed to answer.")
            print_message("Aura", f"Sorry, something went wrong: {exc}")
            continue

        route = routed_response.get("route", {})
        print(
            f"Language: {route.get('language', language_manager.state.name)} | "
            f"Provider: {route.get('provider', 'Unknown')} | "
            f"Model: {route.get('model', 'None')}\n"
        )
        output = build_assistant_output(routed_response)
        print_assistant_output("Aura", output)
        tts_manager.speak(output.spoken_text or output.assistant_message, language_manager.current_language)


if __name__ == "__main__":
    main()
