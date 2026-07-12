import logging
import platform
import re
import subprocess
from pathlib import Path
from shutil import which

from aura_config import (
    LANGUAGE_VOICE_MODELS,
    OUTPUT_DIR,
    PIPER_LINUX_PATH,
    PIPER_WINDOWS_PATH,
)

LOGGER = logging.getLogger(__name__)


class TTSManager:
    def __init__(self) -> None:
        self.piper_path = (
            PIPER_WINDOWS_PATH if platform.system() == "Windows" else PIPER_LINUX_PATH
        )
        self.voice_models = LANGUAGE_VOICE_MODELS
        self.output_dir = OUTPUT_DIR

    def speak(self, text: str, language_code: str) -> None:
        if not text:
            return

        cleaned_text = self.clean_text(text, language_code)
        if not cleaned_text:
            return

        self.output_dir.mkdir(exist_ok=True)
        outfile = self.output_dir / "speech.wav"

        if outfile.exists():
            outfile.unlink()

        try:
            subprocess.run(
                [
                    str(self.piper_path),
                    "--model",
                    str(self._voice_model_for(language_code)),
                    "--output_file",
                    str(outfile),
                ],
                input=cleaned_text,
                text=True,
                encoding="utf-8",
                check=True,
            )
            self._play_audio(outfile)
        except subprocess.CalledProcessError as exc:
            LOGGER.exception("Piper failed.")
            raise RuntimeError("Piper text-to-speech failed.") from exc

    def clean_text(self, text: str, language_code: str) -> str:
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        text = ansi_escape.sub("", text)

        text = text.replace("\u2019", "'").replace("\u2018", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')

        text = re.sub(r'\b\d+DK\b', "", text)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'`(.*?)`', r'\1', text)

        if language_code == "ml":
            text = re.sub(r"[^\u0D00-\u0D7F\s.,!?;:'()\-]", "", text)
        else:
            text = re.sub(r'[^\w\s.,!?;:\'()\-]', "", text)

        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def check_requirements(self) -> list[str]:
        missing = []

        if not self.piper_path.exists():
            missing.append(f"Piper was not found at {self.piper_path}")

        for language_code, voice_model in self.voice_models.items():
            if not voice_model.exists():
                missing.append(
                    f"Voice model for {language_code} was not found at {voice_model}"
                )

        return missing

    def _voice_model_for(self, language_code: str) -> Path:
        try:
            return self.voice_models[language_code]
        except KeyError as exc:
            raise ValueError(f"No voice model configured for language: {language_code}") from exc

    def _play_audio(self, audio_file: Path) -> None:
        if platform.system() == "Windows":
            import winsound

            winsound.PlaySound(str(audio_file), winsound.SND_FILENAME)
            return

        player = "aplay" if which("aplay") else "paplay"
        subprocess.run([player, str(audio_file)], check=True)
