import logging
import re
from dataclasses import dataclass

from aura_config import DEFAULT_LANGUAGE, WHISPER_MALAYALAM_CONFIDENCE

LOGGER = logging.getLogger(__name__)


LANGUAGE_NAMES = {
    "en": "English",
    "ml": "Malayalam",
}


@dataclass
class LanguageState:
    code: str = DEFAULT_LANGUAGE
    manually_locked: bool = False

    @property
    def name(self) -> str:
        return LANGUAGE_NAMES.get(self.code, self.code)


class LanguageManager:
    def __init__(self, default_language: str = DEFAULT_LANGUAGE) -> None:
        self.state = LanguageState(code=default_language)

    @property
    def current_language(self) -> str:
        return self.state.code

    @property
    def is_locked(self) -> bool:
        return self.state.manually_locked

    def system_prompt(self) -> str:
        if self.state.code == "ml":
            return (
                "You are AURA.\n\n"
                "The current conversation language is Malayalam.\n\n"
                "Reply ONLY in Malayalam Unicode.\n\n"
                "Never use English unless the user explicitly requests it.\n\n"
                "Never output Tamil, Telugu or Hindi.\n\n"
                "Never use Latin transliteration.\n\n"
                "Your Malayalam should sound natural and conversational."
            )

        return (
            "You are AURA, a helpful desktop AI assistant.\n\n"
            "Always answer in fluent English.\n\n"
            "Be concise, friendly and conversational."
        )

    def handle_language_command(self, text: str) -> str | None:
        normalized = text.strip().lower()

        malayalam_patterns = [
            r"\bspeak in malayalam\b",
            r"\bchange language to malayalam\b",
            r"\bswitch to malayalam\b",
            r"\buse malayalam\b",
        ]
        english_patterns = [
            r"\bspeak in english\b",
            r"\bchange language to english\b",
            r"\bswitch back to english\b",
            r"\bswitch to english\b",
            r"\buse english\b",
        ]

        if any(re.search(pattern, normalized) for pattern in malayalam_patterns):
            self.set_language("ml", manually_locked=True)
            return "ശരി, ഇനി ഞാൻ മലയാളത്തിൽ സംസാരിക്കും."

        if any(re.search(pattern, normalized) for pattern in english_patterns):
            self.set_language("en", manually_locked=True)
            return "Language changed to English."

        return None

    def set_language(self, language_code: str, manually_locked: bool = False) -> None:
        if language_code not in LANGUAGE_NAMES:
            raise ValueError(f"Unsupported language: {language_code}")

        self.state.code = language_code
        self.state.manually_locked = manually_locked
        LOGGER.info(
            "Conversation language set to %s. Locked=%s",
            language_code,
            manually_locked,
        )

    def update_from_stt_detection(self, language_code: str, confidence: float) -> bool:
        if self.state.manually_locked:
            LOGGER.debug("Skipping STT language switch because language is locked.")
            return False

        if language_code == "ml" and confidence >= WHISPER_MALAYALAM_CONFIDENCE:
            self.set_language("ml", manually_locked=False)
            return True

        return False
