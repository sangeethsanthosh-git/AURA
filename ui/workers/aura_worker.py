"""QThread worker objects for backend and TTS execution."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from ui.controller.aura_controller import AuraController, AuraResponse

LOGGER = logging.getLogger(__name__)


class AuraRequestWorker(QObject):
    """Runs one SmartRouter request away from the UI thread."""

    finished = pyqtSignal(object)

    def __init__(self, controller: AuraController, message: str) -> None:
        super().__init__()
        self.controller = controller
        self.message = message

    @pyqtSlot()
    def run(self) -> None:
        response = self.controller.process_user_message(self.message)
        self.finished.emit(response)


class TTSWorker(QObject):
    """Speaks one response away from the UI thread."""

    finished = pyqtSignal()

    def __init__(self, controller: AuraController, text: str) -> None:
        super().__init__()
        self.controller = controller
        self.text = text

    @pyqtSlot()
    def run(self) -> None:
        try:
            self.controller.speak_response(self.text)
        except Exception:
            LOGGER.warning("TTS worker failed.")
        finally:
            self.finished.emit()


class VoiceTranscriptionWorker(QObject):
    """Stops recording and transcribes away from the UI thread."""

    finished = pyqtSignal(object)

    def __init__(self, controller: AuraController) -> None:
        super().__init__()
        self.controller = controller

    @pyqtSlot()
    def run(self) -> None:
        result = self.controller.stop_voice_recording()
        self.finished.emit(result)
