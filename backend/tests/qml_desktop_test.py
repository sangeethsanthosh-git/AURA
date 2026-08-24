"""Smoke tests for the PySide6/QML desktop shell."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from ui.bridge.aura_bridge import AuraBridge
from ui.controller.aura_controller import ActivityRecord, AuraResponse


class FakeVoiceState:
    value = "IDLE"


class FakeController:
    def __init__(self) -> None:
        self.activities: list[ActivityRecord] = []

    def process_user_message(self, message: str) -> AuraResponse:
        response = AuraResponse("5 + 6 = 11", True, intent="Mathematics", execution_source="Python Math Engine")
        self.activities.append(
            ActivityRecord(message, response.text, response.intent, response.execution_source, response.llm_provider, response.model, response.execution_time, response.success)
        )
        return response

    def list_memories(self) -> list[dict[str, object]]:
        return [{"category": "PREFERENCE", "content": "User prefers local-first AI.", "status": "ACTIVE"}]

    def provider_status(self) -> dict[str, str]:
        return {"Application": "Ready", "TTS": "Disabled"}

    @property
    def voice_state(self) -> FakeVoiceState:
        return FakeVoiceState()

    def start_voice_recording(self):
        return type("Result", (), {"success": False, "error": "fake voice disabled"})()


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication([])
    QQuickStyle.setStyle("Basic")
    failures = 0

    bridge = AuraBridge(FakeController())
    if bridge.backendState != "READY" or bridge.memoryCount != 1:
        print("FAIL bridge did not expose initial runtime state")
        failures += 1

    messages: list[tuple[str, str]] = []
    bridge.messageReceived.connect(lambda role, text, _intent, _source: messages.append((role, text)))
    bridge.sendMessage("What is 5 + 6?")
    deadline = 200
    while len(messages) < 2 and deadline > 0:
        app.processEvents()
        deadline -= 1
    if ("aura", "5 + 6 = 11") not in messages:
        print("FAIL bridge did not emit chat response")
        failures += 1

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("auraBridge", bridge)
    engine.load(QUrl.fromLocalFile(str(PROJECT_ROOT / "ui" / "qml" / "Main.qml")))
    if not engine.rootObjects():
        print("FAIL QML shell did not load")
        failures += 1
    for item in engine.rootObjects():
        item.deleteLater()
    engine.deleteLater()
    for _ in range(20):
        app.processEvents()

    if failures:
        return 1
    print("PASS PySide6 QML desktop shell")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
