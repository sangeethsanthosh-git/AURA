"""Stateful push-to-talk voice input orchestration."""

from __future__ import annotations

from pathlib import Path

from backend.config.config import Settings, settings
from backend.voice.models import TranscriptionResult, VoiceState
from backend.voice.recorder import AudioRecorder, RecordingError, SoundDeviceAudioRecorder, TempAudioFactory
from backend.voice.stt_provider import FasterWhisperProvider, SpeechToTextProvider, SpeechToTextRouter


class VoiceInputManager:
    """Coordinates explicit recording, transcription, and cleanup."""

    def __init__(
        self,
        recorder: AudioRecorder | None = None,
        stt_provider: SpeechToTextProvider | None = None,
        temp_audio_factory: TempAudioFactory | None = None,
        config: Settings = settings,
    ) -> None:
        self.config = config
        self.recorder = recorder or SoundDeviceAudioRecorder()
        self.stt_provider = stt_provider or SpeechToTextRouter(FasterWhisperProvider(config=config))
        self.temp_audio_factory = temp_audio_factory or TempAudioFactory()
        self.state = VoiceState.IDLE
        self.active_audio_path: Path | None = None

    def start_recording(self) -> TranscriptionResult:
        if not self.config.voice_input_enabled:
            return self._error("Voice input is disabled.")
        if self.state == VoiceState.LISTENING:
            return self._result_error("AURA is already listening.")
        if self.state in {VoiceState.STOPPING, VoiceState.TRANSCRIBING}:
            return self._result_error("AURA is still finishing the previous recording.")

        path = self.temp_audio_factory.create()
        try:
            self.recorder.start(path, self.config.max_recording_duration_seconds)
        except Exception as exc:
            self._safe_delete(path)
            return self._error(self._user_error(exc))

        self.active_audio_path = path
        self.state = VoiceState.LISTENING
        return TranscriptionResult(success=True, engine=self.stt_provider.engine)

    def stop_and_transcribe(self) -> TranscriptionResult:
        if self.state != VoiceState.LISTENING or self.active_audio_path is None:
            return self._error("AURA is not currently listening.")

        audio_path = self.active_audio_path
        self.state = VoiceState.STOPPING
        duration = 0.0
        try:
            duration = self.recorder.stop()
            if not audio_path.exists() or audio_path.stat().st_size <= 44:
                return self._error(
                    "I could not capture any speech from the microphone.",
                    duration_seconds=duration,
                )

            self.state = VoiceState.TRANSCRIBING
            result = self.stt_provider.transcribe(audio_path, duration)
            self.state = VoiceState.SUCCESS if result.success else VoiceState.ERROR
            return result
        except Exception as exc:
            return self._error(self._user_error(exc), duration_seconds=duration)
        finally:
            self._safe_delete(audio_path)
            self.active_audio_path = None
            if self.state in {VoiceState.SUCCESS, VoiceState.ERROR, VoiceState.STOPPING, VoiceState.TRANSCRIBING}:
                self.state = VoiceState.IDLE

    def cancel(self) -> TranscriptionResult:
        if self.state != VoiceState.LISTENING:
            return self._error("AURA is not currently listening.")

        audio_path = self.active_audio_path
        try:
            self.recorder.stop()
        except Exception:
            pass
        finally:
            if audio_path is not None:
                self._safe_delete(audio_path)
            self.active_audio_path = None
            self.state = VoiceState.IDLE

        return TranscriptionResult(success=False, engine=self.stt_provider.engine, error="Voice recording cancelled.")

    def _error(self, message: str, duration_seconds: float = 0.0) -> TranscriptionResult:
        self.state = VoiceState.IDLE
        return self._result_error(message, duration_seconds)

    def _result_error(self, message: str, duration_seconds: float = 0.0) -> TranscriptionResult:
        return TranscriptionResult(
            success=False,
            duration_seconds=duration_seconds,
            engine=self.stt_provider.engine,
            error=message,
        )

    @staticmethod
    def _safe_delete(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass

    @staticmethod
    def _user_error(exc: Exception) -> str:
        if isinstance(exc, RecordingError):
            return str(exc)
        return str(exc) or "Voice input failed."
