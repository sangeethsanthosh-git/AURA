"""Voice Studio manager with Piper fallback and profile routing."""

from __future__ import annotations

import hashlib
import logging
import platform
import subprocess
from pathlib import Path
from shutil import which

from aura_config import OUTPUT_DIR, PIPER_LINUX_PATH, PIPER_WINDOWS_PATH
from backend.language.detector import LanguageDetector
from backend.voice_studio.models import SpeechStyle, VoiceEngine, VoiceProfile
from backend.voice_studio.normalization import SpeechNormalizer
from backend.voice_studio.registry import VoiceRegistry

LOGGER = logging.getLogger(__name__)


class VoiceStudioManager:
    def __init__(
        self,
        registry: VoiceRegistry | None = None,
        normalizer: SpeechNormalizer | None = None,
        output_dir: Path = OUTPUT_DIR,
    ) -> None:
        self.registry = registry or VoiceRegistry()
        self.normalizer = normalizer or SpeechNormalizer()
        self.detector = LanguageDetector()
        self.output_dir = output_dir
        self.piper_path = PIPER_WINDOWS_PATH if platform.system() == "Windows" else PIPER_LINUX_PATH
        self.selected_profiles: dict[str, str] = {}
        self.style = SpeechStyle.NATURAL

    def speak(self, text: str, language_code: str = "en", profile_id: str | None = None, speed: float | None = None, style: SpeechStyle | None = None) -> None:
        spoken_text = self.prepare_spoken_text(text, language_code)
        if not spoken_text:
            return
        profile = self.select_profile(language_code, profile_id)
        if not profile.availability:
            raise RuntimeError(f"Voice profile unavailable: {profile.display_name}. {profile.unavailable_reason or ''}".strip())
        if profile.engine != VoiceEngine.PIPER:
            raise RuntimeError(f"Voice engine is not implemented yet: {profile.engine}")
        self._speak_with_piper(spoken_text, profile)

    def prepare_spoken_text(self, text: str, language_code: str = "en") -> str:
        detected = self.detector.detect(text)
        route_code = detected.code if detected.code != "other" else language_code
        return self.normalizer.normalize(text, route_code)

    def select_profile(self, language_code: str, profile_id: str | None = None) -> VoiceProfile:
        if profile_id:
            profile = self.registry.get(profile_id)
            if profile:
                return profile
        selected = self.selected_profiles.get(language_code)
        if selected and (profile := self.registry.get(selected)):
            return profile
        return self.registry.default_for_language(language_code)

    def set_profile(self, language_code: str, profile_id: str) -> bool:
        if not self.registry.get(profile_id):
            return False
        self.selected_profiles[language_code] = profile_id
        return True

    def preview_text(self, profile_id: str) -> str:
        profile = self.registry.get(profile_id)
        if not profile:
            return "Voice profile not found."
        if "ml" in profile.supported_languages:
            return "എന്താ വേണ്ടത്? ഞാൻ സഹായിക്കാം."
        return "Hello. I am AURA. How can I help?"

    def capability_status(self) -> dict[str, object]:
        profiles = []
        for profile in self.registry.profiles():
            profiles.append(
                {
                    "id": profile.id,
                    "display_name": profile.display_name,
                    "engine": profile.engine.value,
                    "languages": profile.supported_languages,
                    "available": profile.availability,
                    "reason": profile.unavailable_reason,
                }
            )
        return {"profiles": profiles, "active_style": self.style.value}

    def _speak_with_piper(self, text: str, profile: VoiceProfile) -> None:
        self.output_dir.mkdir(exist_ok=True)
        outfile = self.output_dir / self._audio_name(text, profile)
        if not outfile.exists():
            try:
                subprocess.run(
                    [str(self.piper_path), "--model", str(profile.model_reference), "--output_file", str(outfile)],
                    input=text,
                    text=True,
                    encoding="utf-8",
                    check=True,
                )
            except subprocess.CalledProcessError as exc:
                LOGGER.exception("Piper failed.")
                raise RuntimeError("Piper text-to-speech failed.") from exc
        self._play_audio(outfile)

    @staticmethod
    def _audio_name(text: str, profile: VoiceProfile) -> str:
        digest = hashlib.sha256(f"{profile.id}\n{text}".encode("utf-8")).hexdigest()[:16]
        return f"speech_{digest}.wav"

    @staticmethod
    def _play_audio(audio_file: Path) -> None:
        if platform.system() == "Windows":
            import winsound

            winsound.PlaySound(str(audio_file), winsound.SND_FILENAME)
            return
        player = "aplay" if which("aplay") else "paplay"
        subprocess.run([player, str(audio_file)], check=True)
