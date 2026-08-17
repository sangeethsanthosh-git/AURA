"""Regression tests for on-demand voice input."""

from __future__ import annotations

import os
import sys
import tempfile
import time
import wave
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication

from backend.config.config import Settings
from backend.voice.manager import VoiceInputManager
from backend.voice.models import TranscriptionResult, VoiceState
from ui.controller.aura_controller import ActivityRecord, AuraResponse
from ui.main_window import MainWindow


class TempFactory:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.paths: list[Path] = []

    def create(self) -> Path:
        path = self.root / f"voice_{len(self.paths)}.wav"
        self.paths.append(path)
        return path


class FakeRecorder:
    def __init__(self, write_audio: bool = True, fail_start: bool = False, fail_stop: bool = False) -> None:
        self.write_audio = write_audio
        self.fail_start = fail_start
        self.fail_stop = fail_stop
        self.started = False
        self.stopped = False
        self.path: Path | None = None

    def start(self, path: Path, max_duration_seconds: float) -> None:
        if self.fail_start:
            raise RuntimeError("microphone unavailable")
        self.started = True
        self.path = path

    def stop(self) -> float:
        if self.fail_stop:
            raise RuntimeError("recording failure")
        self.stopped = True
        if self.path is not None:
            if self.write_audio:
                with wave.open(str(self.path), "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(16000)
                    wav.writeframes(b"\1\0" * 160)
            else:
                self.path.write_bytes(b"")
        return 0.2


class FakeProvider:
    engine = "fake-stt"

    def __init__(self, result: TranscriptionResult | None = None) -> None:
        self.result = result or TranscriptionResult(True, "What is five times eight?", "en", 0.91, 0.2, self.engine)
        self.calls = 0

    def transcribe(self, audio_path: Path, duration_seconds: float = 0.0) -> TranscriptionResult:
        self.calls += 1
        return TranscriptionResult(
            success=self.result.success,
            text=self.result.text,
            language=self.result.language,
            confidence=self.result.confidence,
            duration_seconds=duration_seconds,
            engine=self.engine,
            error=self.result.error,
        )


class FakeRouter:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def ask(self, message: str) -> dict[str, object]:
        self.messages.append(message)
        return {
            "ok": True,
            "provider": "math",
            "action": "calculate",
            "message": "The answer is 40.",
            "data": {},
            "route": {
                "intent": "Mathematics",
                "provider": "Python Math Engine",
                "model": "None",
                "source": "Python Math Engine",
                "execution_time_seconds": 0.01,
            },
        }


class VoiceFakeController:
    def __init__(self, delay: float = 0.0) -> None:
        self.delay = delay
        self.tts_enabled = False
        self.activities: list[ActivityRecord] = []
        self.started = False

    def start_voice_recording(self) -> TranscriptionResult:
        self.started = True
        return TranscriptionResult(True, engine="fake-stt")

    def stop_voice_recording(self) -> TranscriptionResult:
        time.sleep(self.delay)
        return TranscriptionResult(True, "Hello AURA", "en", 0.9, 0.1, "fake-stt")

    def process_user_message(self, message: str) -> AuraResponse:
        response = AuraResponse("ok", True)
        self.activities.insert(0, ActivityRecord(message, response.text, "Conversation", "Fake", "None", "None", 0.0, True))
        return response

    def list_memories(self) -> list[dict[str, object]]:
        return []

    def forget_memory(self, content: str) -> AuraResponse:
        return AuraResponse("ok", True)

    def speak_response(self, text: str) -> None:
        return None


def make_manager(root: Path, recorder: FakeRecorder, provider: FakeProvider) -> VoiceInputManager:
    return VoiceInputManager(
        recorder=recorder,
        stt_provider=provider,
        temp_audio_factory=TempFactory(root),
        config=Settings(max_recording_duration_seconds=1),
    )


def pump_until(condition, timeout: float = 2.0) -> bool:
    app = QApplication.instance()
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return condition()


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        recorder = FakeRecorder()
        provider = FakeProvider()
        manager = make_manager(root, recorder, provider)
        if manager.state != VoiceState.IDLE:
            print("FAIL voice manager did not initialize idle")
            failures += 1

        started = manager.start_recording()
        if not started.success or manager.state != VoiceState.LISTENING or not recorder.started:
            print("FAIL start recording did not enter listening state")
            failures += 1

        duplicate = manager.start_recording()
        if duplicate.success:
            print("FAIL duplicate start request was accepted")
            failures += 1

        result = manager.stop_and_transcribe()
        if not result.success or result.text != "What is five times eight?" or manager.state != VoiceState.IDLE:
            print("FAIL successful transcription result/state was wrong")
            failures += 1
        if provider.calls != 1:
            print("FAIL STT provider was not called exactly once")
            failures += 1
        if any(path.exists() for path in manager.temp_audio_factory.paths):
            print("FAIL temporary audio was not cleaned up")
            failures += 1

        empty = make_manager(root, FakeRecorder(write_audio=False), FakeProvider())
        empty.start_recording()
        empty_result = empty.stop_and_transcribe()
        if empty_result.success or "capture any speech" not in (empty_result.error or ""):
            print("FAIL empty recording was not handled cleanly")
            failures += 1

        failed_stt = make_manager(
            root,
            FakeRecorder(),
            FakeProvider(TranscriptionResult(False, engine="fake-stt", error="missing STT model")),
        )
        failed_stt.start_recording()
        failed_result = failed_stt.stop_and_transcribe()
        if failed_result.success or failed_result.error != "missing STT model":
            print("FAIL failed transcription was not returned cleanly")
            failures += 1

        failed_mic = make_manager(root, FakeRecorder(fail_start=True), FakeProvider())
        mic_result = failed_mic.start_recording()
        if mic_result.success or failed_mic.state != VoiceState.IDLE:
            print("FAIL microphone failure left invalid state")
            failures += 1

        failed_stop = make_manager(root, FakeRecorder(fail_stop=True), FakeProvider())
        failed_stop.start_recording()
        stop_result = failed_stop.stop_and_transcribe()
        if stop_result.success or failed_stop.state != VoiceState.IDLE:
            print("FAIL recording stop failure left invalid state")
            failures += 1

        router = FakeRouter()
        from ui.controller.aura_controller import AuraController

        controller = AuraController(router=router, voice_manager=make_manager(root, FakeRecorder(), FakeProvider()))
        voice_result = controller.start_voice_recording()
        transcript = controller.stop_voice_recording()
        response = controller.process_user_message(transcript.text)
        if not voice_result.success or not response.success or router.messages != ["What is five times eight?"]:
            print("FAIL voice transcription did not enter same AURA pipeline")
            failures += 1

        typed_response = controller.process_user_message("typed chat still works")
        if not typed_response.success or router.messages[-1] != "typed chat still works":
            print("FAIL existing typed chat compatibility broke")
            failures += 1

    app = QApplication.instance() or QApplication([])
    window = MainWindow(VoiceFakeController(delay=0.2))
    started_at = time.perf_counter()
    window.toggle_voice_input()
    window.toggle_voice_input()
    app.processEvents()
    if time.perf_counter() - started_at > 0.1:
        print("FAIL voice transcription blocked the UI thread")
        failures += 1
    if not pump_until(lambda: window.voice_thread is None):
        print("FAIL voice transcription worker did not finish")
        failures += 1
    if window.chat_page.input.toPlainText().strip() != "Hello AURA":
        print("FAIL UI did not place transcript in input field")
        failures += 1

    if failures:
        return 1
    print("PASS on-demand voice input behavior")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
