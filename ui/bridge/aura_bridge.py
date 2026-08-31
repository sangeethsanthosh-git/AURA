"""Controlled PySide6 bridge exposed to QML."""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from PySide6.QtCore import QObject, Property, QThread, Signal, Slot

from ui.controller.aura_controller import AuraController, AuraResponse

LOGGER = logging.getLogger(__name__)


class BackendInitWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    @Slot()
    def run(self) -> None:
        try:
            self.finished.emit(AuraController())
        except Exception as exc:  # pragma: no cover - defensive startup path
            LOGGER.exception("QML backend initialization failed.")
            self.failed.emit(str(exc))


class MessageWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, controller: AuraController, message: str) -> None:
        super().__init__()
        self.controller = controller
        self.message = message

    @Slot()
    def run(self) -> None:
        try:
            self.finished.emit(self.controller.process_user_message(self.message))
        except Exception as exc:  # pragma: no cover - defensive worker path
            LOGGER.exception("QML message processing failed.")
            self.failed.emit(str(exc))


class AuraBridge(QObject):
    """Small, safe surface for QML. The AI/backend stays in Python."""

    backendStateChanged = Signal()
    appStateChanged = Signal()
    statusSummaryChanged = Signal()
    memoryCountChanged = Signal()
    activityCountChanged = Signal()
    voiceStateChanged = Signal()
    messageReceived = Signal(str, str, str, str)
    providerStatusChanged = Signal("QVariant")
    errorOccurred = Signal(str)

    def __init__(self, controller: AuraController | None = None) -> None:
        super().__init__()
        self._controller = controller
        self._backend_state = "READY" if controller else "STARTING"
        self._app_state = "IDLE"
        self._status_summary = "Starting local AURA backend..."
        self._memory_count = 0
        self._activity_count = 0
        self._voice_state = "IDLE"
        self._threads: list[QThread] = []
        self._workers: list[QObject] = []
        if controller:
            self._refresh_runtime()

    @Property(str, notify=backendStateChanged)
    def backendState(self) -> str:
        return self._backend_state

    @Property(str, notify=appStateChanged)
    def appState(self) -> str:
        return self._app_state

    @Property(str, notify=statusSummaryChanged)
    def statusSummary(self) -> str:
        return self._status_summary

    @Property(int, notify=memoryCountChanged)
    def memoryCount(self) -> int:
        return self._memory_count

    @Property(int, notify=activityCountChanged)
    def activityCount(self) -> int:
        return self._activity_count

    @Property(str, notify=voiceStateChanged)
    def voiceState(self) -> str:
        return self._voice_state

    @Slot()
    def initializeBackend(self) -> None:
        if self._controller is not None:
            self._set_backend_state("READY")
            return
        self._set_backend_state("STARTING")
        thread = QThread(self)
        worker = BackendInitWorker()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_backend_ready)
        worker.failed.connect(self._handle_backend_error)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._threads.remove(thread) if thread in self._threads else None)
        thread.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        self._threads.append(thread)
        self._workers.append(worker)
        thread.start()

    @Slot(str)
    def sendMessage(self, message: str) -> None:
        clean = message.strip()
        if not clean:
            return
        self.messageReceived.emit("user", clean, "", "")
        if self._controller is None:
            self.messageReceived.emit("system", "AURA backend is not ready yet.", "OFFLINE", "")
            return

        self._set_app_state("OBSERVING" if self._is_screen_request(clean) else "THINKING")
        thread = QThread(self)
        worker = MessageWorker(self._controller, clean)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_message_response)
        worker.failed.connect(self._handle_message_error)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._threads.remove(thread) if thread in self._threads else None)
        thread.finished.connect(lambda: self._workers.remove(worker) if worker in self._workers else None)
        self._threads.append(thread)
        self._workers.append(worker)
        thread.start()

    @Slot()
    def retryBackend(self) -> None:
        self.initializeBackend()

    @Slot(result="QVariant")
    def getSystemStatus(self) -> dict[str, Any]:
        if not self._controller:
            return {"Backend": self._backend_state}
        return {"Backend": self._backend_state, **self._controller.provider_status()}

    @Slot(result="QVariant")
    def getMemorySummary(self) -> dict[str, Any]:
        if not self._controller:
            return {"count": 0, "items": []}
        items = self._controller.list_memories()
        return {"count": len(items), "items": items[:5]}

    @Slot(result=str)
    def getVoiceStatus(self) -> str:
        return self._voice_state

    @Slot(result="QVariant")
    def getVisionStatus(self) -> dict[str, Any]:
        if not self._controller:
            return {
                "state": "UNAVAILABLE",
                "eyes_active": False,
                "ocr_available": False,
                "vision_available": False,
                "active_window_inspection": False,
                "continuous_capture": False,
                "languages": [],
            }
        return self._controller.vision_status()

    @Slot()
    def startListening(self) -> None:
        if not self._controller:
            self.errorOccurred.emit("Voice is unavailable until the backend is ready.")
            return
        result = self._controller.start_voice_recording()
        if result.success:
            self._set_voice_state("LISTENING")
            self._set_app_state("LISTENING")
        else:
            self.errorOccurred.emit(result.error or "Voice input could not start.")

    @Slot()
    def stopListening(self) -> None:
        if not self._controller:
            return
        result = self._controller.stop_voice_recording()
        self._set_voice_state("IDLE")
        self._set_app_state("IDLE")
        if result.success and result.text.strip():
            self.sendMessage(result.text.strip())
        else:
            self.errorOccurred.emit(result.error or "I could not transcribe that recording.")

    def _handle_backend_ready(self, controller: AuraController) -> None:
        self._controller = controller
        self._status_summary = "AURA backend ready."
        self.statusSummaryChanged.emit()
        self._set_backend_state("READY")
        self._refresh_runtime()

    def _handle_backend_error(self, error: str) -> None:
        self._status_summary = "AURA backend is offline."
        self.statusSummaryChanged.emit()
        self._set_backend_state("ERROR")
        self.errorOccurred.emit(error)

    def _handle_message_response(self, response: AuraResponse) -> None:
        role = "aura" if response.success else "system"
        self.messageReceived.emit(role, response.text, response.intent, response.execution_source)
        self._set_app_state("IDLE" if response.success else "ERROR")
        self._refresh_runtime()

    def _handle_message_error(self, error: str) -> None:
        self.messageReceived.emit("system", "AURA encountered a problem while processing that request.", "ERROR", "")
        self._set_app_state("ERROR")
        self.errorOccurred.emit(error)

    def _refresh_runtime(self) -> None:
        if not self._controller:
            return
        memories = self._controller.list_memories()
        self._memory_count = len(memories)
        self.memoryCountChanged.emit()
        self._activity_count = len(self._controller.activities)
        self.activityCountChanged.emit()
        self._voice_state = str(self._controller.voice_state.value)
        self.voiceStateChanged.emit()
        self.providerStatusChanged.emit(self._controller.provider_status())

    def _set_backend_state(self, state: str) -> None:
        if self._backend_state != state:
            self._backend_state = state
            self.backendStateChanged.emit()

    def _set_app_state(self, state: str) -> None:
        if self._app_state != state:
            self._app_state = state
            self.appStateChanged.emit()

    def _set_voice_state(self, state: str) -> None:
        if self._voice_state != state:
            self._voice_state = state
            self.voiceStateChanged.emit()

    @staticmethod
    def _is_screen_request(message: str) -> bool:
        lowered = message.lower()
        return "screen" in lowered and any(term in lowered for term in ("look", "read", "analyze", "inspect", "what is"))
