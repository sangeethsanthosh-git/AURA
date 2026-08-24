"""Main window for AURA Desktop."""

from __future__ import annotations

from PyQt6.QtCore import QSettings, QThread, Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QFileDialog,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.activity_page import ActivityPage
from ui.chat_page import ChatPage
from ui.controller.aura_controller import AuraController, AuraResponse
from ui.memory_page import MemoryPage
from ui.settings_page import SettingsPage
from ui.theme import APP_STYLE
from ui.widgets.status_indicator import StatusIndicator
from ui.workers.aura_worker import AuraRequestWorker, TTSWorker, VoiceTranscriptionWorker


class MainWindow(QMainWindow):
    """Primary PyQt6 shell for AURA."""

    def __init__(self, controller: AuraController | None = None) -> None:
        super().__init__()
        self.controller = controller or AuraController()
        self.request_thread: QThread | None = None
        self.request_worker: AuraRequestWorker | None = None
        self.tts_threads: list[QThread] = []
        self.tts_workers: list[TTSWorker] = []
        self.voice_thread: QThread | None = None
        self.voice_worker: VoiceTranscriptionWorker | None = None
        self.is_listening = False

        self.setWindowTitle("AURA ASUS")
        self.setMinimumSize(900, 620)
        self.setStyleSheet(APP_STYLE)

        self.status_indicator = StatusIndicator()
        self.stack = QStackedWidget()
        self.chat_page = ChatPage()
        self.activity_page = ActivityPage()
        self.memory_page = MemoryPage()
        self.settings_page = SettingsPage()

        for page in (self.chat_page, self.memory_page, self.activity_page, self.settings_page):
            self.stack.addWidget(page)

        self.nav_buttons: list[QPushButton] = []
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self._top_bar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.addWidget(self._sidebar())
        body.addWidget(self.stack, 1)
        root_layout.addLayout(body, 1)
        self.setCentralWidget(root)

        self.chat_page.send_requested.connect(self.send_message)
        self.chat_page.attach_requested.connect(self.attach_file)
        self.chat_page.microphone_requested.connect(self.toggle_voice_input)
        self.memory_page.refresh_requested.connect(self.refresh_memory)
        self.memory_page.forget_requested.connect(self.forget_memory)
        self.settings_page.tts_changed.connect(self._set_tts_enabled)
        self._select_page(0)
        self.refresh_memory()
        self._restore_geometry()

    def send_message(self, message: str) -> None:
        if self.request_thread is not None:
            return
        self.chat_page.add_user_message(message)
        if self._is_screen_request(message):
            self.chat_page.add_aura_message("AURA is looking at your screen...")
        if self._is_web_request(message):
            self.chat_page.add_aura_message("Searching the web...")
        self.chat_page.set_processing(True)
        self.status_indicator.set_processing()

        thread = QThread(self)
        worker = AuraRequestWorker(self.controller, message)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_response)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: setattr(self, "request_thread", None))
        thread.finished.connect(lambda: setattr(self, "request_worker", None))
        self.request_thread = thread
        self.request_worker = worker
        thread.start()

    def attach_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select document",
            "",
            "Documents (*.txt *.md *.pdf)",
        )
        if path:
            self.send_message(f"Analyze file {path}")

    def toggle_voice_input(self) -> None:
        if self.voice_thread is not None:
            return
        if not self.is_listening:
            result = self.controller.start_voice_recording()
            if result.success:
                self.is_listening = True
                self.chat_page.set_voice_state("Stop", listening=True)
                self.status_indicator.set_processing()
            else:
                self.status_indicator.set_error()
                self.chat_page.add_aura_message(result.error or "Voice input could not start.")
            return

        self.is_listening = False
        self.chat_page.set_voice_state("Transcribing", busy=True)
        thread = QThread(self)
        worker = VoiceTranscriptionWorker(self.controller)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_voice_result)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: setattr(self, "voice_thread", None))
        thread.finished.connect(lambda: setattr(self, "voice_worker", None))
        self.voice_thread = thread
        self.voice_worker = worker
        thread.start()

    def refresh_memory(self) -> None:
        self.memory_page.refresh_memories(self.controller.list_memories())

    def forget_memory(self, content: str) -> None:
        response = self.controller.forget_memory(content)
        if response.success:
            self.refresh_memory()
        else:
            QMessageBox.warning(self, "AURA Memory", response.text)

    def closeEvent(self, event) -> None:
        settings = QSettings("AURA", "AURA ASUS")
        settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

    def _handle_response(self, response: AuraResponse) -> None:
        self.chat_page.set_processing(False)
        if response.success:
            self.status_indicator.set_ready()
            self.chat_page.add_aura_message(response.text)
            self._start_tts(response.spoken_text or response.text)
            if self._maybe_confirm_action(response):
                return
        else:
            self.status_indicator.set_error()
            self.chat_page.add_aura_message(response.text or "AURA encountered a problem while processing that request.")
        self.activity_page.refresh(self.controller.activities)
        self.refresh_memory()

    def _maybe_confirm_action(self, response: AuraResponse) -> bool:
        data = response.raw.get("data", {}) if isinstance(response.raw, dict) else {}
        pending = data.get("pending_confirmation") if isinstance(data, dict) else None
        if not pending:
            return False
        if isinstance(pending, dict):
            action = str(pending.get("action_type", "action")).replace("_", " ")
            target = str(pending.get("target", ""))
        else:
            task = data.get("task", {}) if isinstance(data, dict) else {}
            steps = task.get("steps", []) if isinstance(task, dict) else []
            current = int(task.get("current_step", 0) or 0) if isinstance(task, dict) else 0
            step = steps[current] if current < len(steps) else {}
            action_data = step.get("action", {}) if isinstance(step, dict) else {}
            action = str(action_data.get("action_type", "task action")).replace("_", " ")
            target = str(action_data.get("target", ""))
        decision = QMessageBox.question(
            self,
            "Confirm AURA Action",
            f"AURA wants to perform:\n\n{action}\n\nTarget:\n{target}\n\nProceed?",
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.Cancel,
        )
        self.activity_page.refresh(self.controller.activities)
        self.refresh_memory()
        if decision == QMessageBox.StandardButton.Yes:
            self.send_message("yes")
        else:
            self.send_message("cancel")
        return True

    def _handle_voice_result(self, result) -> None:
        self.chat_page.set_voice_state("Mic")
        if result.success and result.text.strip():
            self.status_indicator.set_ready()
            self.chat_page.set_input_text(result.text.strip())
        else:
            self.status_indicator.set_error()
            self.chat_page.add_aura_message(result.error or "I could not transcribe that recording.")

    def _start_tts(self, text: str) -> None:
        if not self.controller.tts_enabled:
            return
        thread = QThread(self)
        worker = TTSWorker(self.controller, text)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda: self.tts_workers.remove(worker) if worker in self.tts_workers else None)
        thread.finished.connect(lambda: self.tts_threads.remove(thread) if thread in self.tts_threads else None)
        thread.finished.connect(thread.deleteLater)
        self.tts_threads.append(thread)
        self.tts_workers.append(worker)
        thread.start()

    def _top_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("card")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 12, 18, 12)
        title = QLabel("AURA ASUS")
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.status_indicator)
        return bar

    def _sidebar(self) -> QWidget:
        side = QFrame()
        side.setFixedWidth(170)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(14, 18, 14, 18)
        layout.setSpacing(10)
        for index, label in enumerate(("Chat", "Memory", "Activity", "Settings")):
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda _, i=index: self._select_page(i))
            self.nav_buttons.append(button)
            layout.addWidget(button)
        layout.addStretch()
        return side

    def _select_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for item, button in enumerate(self.nav_buttons):
            button.setChecked(item == index)
        if index == 1:
            self.refresh_memory()
        if index == 2:
            self.activity_page.refresh(self.controller.activities)

    def _set_tts_enabled(self, enabled: bool) -> None:
        self.controller.tts_enabled = enabled

    @staticmethod
    def _is_screen_request(message: str) -> bool:
        lowered = message.lower()
        return "screen" in lowered and any(term in lowered for term in ("look", "read", "analyze", "inspect", "what is"))

    @staticmethod
    def _is_web_request(message: str) -> bool:
        lowered = message.lower()
        return any(term in lowered for term in ("latest", "recent", "currently", "current version", "today", "news"))

    def _restore_geometry(self) -> None:
        settings = QSettings("AURA", "AURA ASUS")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
