"""Speech-text normalization for display-to-voice conversion."""

from __future__ import annotations

import re
import unicodedata

from backend.language.detector import LanguageDetector, LanguageRoute


class SpeechNormalizer:
    URL_RE = re.compile(r"https?://\S+")
    CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)

    ABBREVIATIONS = {
        "AI": "A I",
        "API": "A P I",
        "RAG": "R A G",
        "LLM": "L L M",
        "URL": "U R L",
    }

    def __init__(self, detector: LanguageDetector | None = None) -> None:
        self.detector = detector or LanguageDetector()

    def normalize(self, text: str, language_code: str | None = None) -> str:
        text = unicodedata.normalize("NFC", text)
        text = self.CODE_BLOCK_RE.sub("I have included code in the displayed response.", text)
        text = self.URL_RE.sub("a link", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\*\*([^*]+)\*\*|\*([^*]+)\*", lambda m: m.group(1) or m.group(2), text)
        text = text.replace("°C", " degrees Celsius")
        for source, target in self.ABBREVIATIONS.items():
            text = re.sub(rf"\b{source}\b", target, text)
        route = self.detector.detect(text).route if language_code in {None, "mixed"} else None
        if language_code == "ml" or route == LanguageRoute.MALAYALAM:
            return self._normalize_malayalam(text)
        return self._normalize_general(text)

    @staticmethod
    def _normalize_general(text: str) -> str:
        text = re.sub(r"[_#<>|{}\[\]]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _normalize_malayalam(text: str) -> str:
        # Preserve Malayalam Unicode and embedded English technical terms.
        text = re.sub(r"[<>|{}\[\]]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
