import logging
import re
from pathlib import Path

from backend.voice_studio.manager import VoiceStudioManager
LOGGER = logging.getLogger(__name__)


class TTSManager:
    """Compatibility wrapper around AURA Voice Studio."""

    def __init__(self, voice_studio: VoiceStudioManager | None = None) -> None:
        self.voice_studio = voice_studio or VoiceStudioManager()
        self.piper_path = self.voice_studio.piper_path
        self.voice_models = {
            "en": Path(self.voice_studio.registry.get("piper-en-ljspeech-high").model_reference),  # type: ignore[union-attr]
            "ml": Path(self.voice_studio.registry.get("piper-ml-meera").model_reference),  # type: ignore[union-attr]
        }
        self.output_dir = self.voice_studio.output_dir

    def speak(self, text: str, language_code: str) -> None:
        self.voice_studio.speak(text, language_code)

    def clean_text(self, text: str, language_code: str) -> str:
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return self.voice_studio.prepare_spoken_text(ansi_escape.sub("", text), language_code)

    def check_requirements(self) -> list[str]:
        missing = []

        for profile in self.voice_studio.registry.profiles():
            if profile.engine.value == "piper" and not profile.availability:
                missing.append(profile.unavailable_reason or f"Voice profile unavailable: {profile.display_name}")

        return missing

    def _voice_model_for(self, language_code: str) -> Path:
        return Path(self.voice_studio.select_profile(language_code).model_reference)

    def _play_audio(self, audio_file: Path) -> None:
        self.voice_studio._play_audio(audio_file)
