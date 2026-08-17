"""Smoke tests for the PyQt6 desktop interface."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from ui.controller.aura_controller import ActivityRecord, AuraResponse
from ui.main_window import MainWindow


class FakeController:
    def __init__(self, delay: float = 0.0, fail: bool = False) -> None:
        self.delay = delay
        self.fail = fail
        self.tts_enabled = False
        self.spoken: list[str] = []
        self.activities: list[ActivityRecord] = []

    def process_user_message(self, message: str) -> AuraResponse:
        time.sleep(self.delay)
        if self.fail:
            response = AuraResponse("AURA encountered a problem while processing that request.", False, error="fake failure")
        else:
            response = AuraResponse("The result is 40.", True, intent="Mathematics", execution_source="Python Math Engine", execution_time=0.01)
        self.activities.insert(
            0,
            ActivityRecord(message, response.text, response.intent, response.execution_source, response.llm_provider, response.model, response.execution_time, response.success, response.error),
        )
        return response

    def list_memories(self) -> list[dict[str, object]]:
        return [{"category": "PREFERENCE", "content": "User prefers Python.", "status": "ACTIVE"}]

    def forget_memory(self, content: str) -> AuraResponse:
        return AuraResponse(f"Forgot {content}", True)

    def speak_response(self, text: str) -> None:
        raise RuntimeError("fake TTS failure")


def pump_until(condition, timeout: float = 2.0) -> bool:
    deadline = time.time() + timeout
    app = QApplication.instance()
    while time.time() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return condition()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    failures = 0

    window = MainWindow(FakeController())
    window.show()
    app.processEvents()
    if not window.isVisible():
        print("FAIL application window did not start")
        failures += 1

    slow = MainWindow(FakeController(delay=0.2))
    started = time.perf_counter()
    slow.send_message("What is 5 x 8?")
    app.processEvents()
    if time.perf_counter() - started > 0.1:
        print("FAIL send_message blocked the UI thread")
        failures += 1
    if not pump_until(lambda: slow.request_thread is None):
        print("FAIL backend worker did not finish")
        failures += 1
    if not slow.controller.activities or slow.controller.activities[0].intent != "Mathematics":
        print("FAIL activity metadata was not recorded")
        failures += 1

    failing = MainWindow(FakeController(fail=True))
    failing.send_message("trigger error")
    if not pump_until(lambda: failing.request_thread is None):
        print("FAIL error worker did not finish")
        failures += 1
    if not failing.controller.activities or failing.controller.activities[0].success:
        print("FAIL backend error was not represented cleanly")
        failures += 1

    tts = MainWindow(FakeController())
    tts.controller.tts_enabled = True
    tts._start_tts("hello")
    if not pump_until(lambda: not tts.tts_threads):
        print("FAIL TTS worker failure was not contained")
        failures += 1

    QTimer.singleShot(0, app.quit)
    if failures:
        return 1
    print("PASS PyQt6 desktop UI smoke behavior")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
