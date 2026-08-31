"""Central voice registry for Piper and future Indic engines."""

from __future__ import annotations

import platform
from pathlib import Path

from aura_config import LANGUAGE_VOICE_MODELS, PIPER_LINUX_PATH, PIPER_WINDOWS_PATH
from backend.voice_studio.models import SpeechStyle, VoiceEngine, VoiceLanguage, VoiceProfile


class VoiceRegistry:
    def __init__(self) -> None:
        self.piper_path = PIPER_WINDOWS_PATH if platform.system() == "Windows" else PIPER_LINUX_PATH
        self._profiles = self._build_profiles()

    def profiles(self) -> list[VoiceProfile]:
        return list(self._profiles.values())

    def get(self, profile_id: str) -> VoiceProfile | None:
        return self._profiles.get(profile_id)

    def default_for_language(self, language_code: str) -> VoiceProfile:
        if language_code == "ml":
            return self._profiles["piper-ml-meera"]
        if language_code == "mixed":
            return self._profiles["piper-ml-meera"] if self._profiles["piper-ml-meera"].availability else self.default_for_language("en")
        return self._profiles["piper-en-ljspeech-high"] if self._profiles["piper-en-ljspeech-high"].availability else self._profiles["piper-en-lessac"]

    def _build_profiles(self) -> dict[str, VoiceProfile]:
        en_model = LANGUAGE_VOICE_MODELS.get("en", Path(""))
        en_lessac_model = LANGUAGE_VOICE_MODELS.get("en_lessac", Path(""))
        ml_model = LANGUAGE_VOICE_MODELS.get("ml", Path(""))
        piper_ready = self.piper_path.exists()
        profiles = [
            VoiceProfile(
                "piper-en-ljspeech-high",
                "Piper English Natural High",
                VoiceEngine.PIPER,
                VoiceLanguage.ENGLISH,
                ("en",),
                en_model,
                piper_ready and en_model.exists(),
                "Higher-quality local Piper English voice for the AI Assistant companion.",
                speaker="ljspeech",
                supported_styles=(SpeechStyle.NATURAL, SpeechStyle.FRIENDLY, SpeechStyle.CALM),
                unavailable_reason=None if piper_ready and en_model.exists() else "Piper executable or high-quality English model missing.",
            ),
            VoiceProfile(
                "piper-en-lessac",
                "Piper English Lessac",
                VoiceEngine.PIPER,
                VoiceLanguage.ENGLISH,
                ("en",),
                en_lessac_model,
                piper_ready and en_lessac_model.exists(),
                "Existing lightweight local Piper English voice.",
                speaker="lessac",
                supported_styles=(SpeechStyle.NATURAL, SpeechStyle.PROFESSIONAL, SpeechStyle.CALM),
                unavailable_reason=None if piper_ready and en_lessac_model.exists() else "Piper executable or English Lessac model missing.",
            ),
            VoiceProfile(
                "piper-ml-meera",
                "Piper Malayalam Meera",
                VoiceEngine.PIPER,
                VoiceLanguage.MALAYALAM,
                ("ml", "mixed"),
                ml_model,
                piper_ready and ml_model.exists(),
                "Existing local Piper Malayalam voice; used as Malayalam fallback.",
                speaker="meera",
                supported_styles=(SpeechStyle.NATURAL, SpeechStyle.CALM),
                unavailable_reason=None if piper_ready and ml_model.exists() else "Piper executable or Malayalam model missing.",
            ),
            VoiceProfile(
                "indicf5-auto",
                "IndicF5 Candidate",
                VoiceEngine.INDIC_F5,
                VoiceLanguage.MIXED,
                ("ml", "en", "mixed"),
                "ai4bharat/IndicF5",
                False,
                "Candidate multilingual TTS engine. Not installed or benchmarked in this project yet.",
                supported_styles=tuple(SpeechStyle),
                unavailable_reason="Requires benchmark and local model setup before use.",
            ),
            VoiceProfile(
                "indic-parler-auto",
                "Indic Parler-TTS Candidate",
                VoiceEngine.INDIC_PARLER,
                VoiceLanguage.MIXED,
                ("ml", "en", "mixed"),
                "ai4bharat/indic-parler-tts",
                False,
                "Candidate natural Indian-language TTS engine. Not installed or benchmarked in this project yet.",
                supported_styles=tuple(SpeechStyle),
                unavailable_reason="Requires benchmark and local model setup before use.",
            ),
        ]
        return {profile.id: profile for profile in profiles}
