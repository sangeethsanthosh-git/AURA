"""Main chat page for AURA Desktop."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.chat_message import ChatMessage


class PromptEdit(QTextEdit):
    """Text box where Enter sends and Shift+Enter inserts a newline."""

    send_requested = pyqtSignal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter} and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.send_requested.emit()
            return
        super().keyPressEvent(event)


class ChatPage(QWidget):
    """Conversation UI with a bounded session display."""

    send_requested = pyqtSignal(str)
    attach_requested = pyqtSignal()
    microphone_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.thinking_widget: QLabel | None = None

        title = QLabel("AURA")
        title.setObjectName("title")
        subtitle = QLabel("How can I help you?")
        subtitle.setObjectName("subtitle")

        self.message_container = QWidget()
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setContentsMargins(24, 24, 24, 24)
        self.message_layout.setSpacing(14)
        self.message_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.message_layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.message_layout.addStretch()

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.message_container)

        self.input = PromptEdit()
        self.input.setPlaceholderText("Ask AURA anything...")
        self.input.setFixedHeight(72)
        self.input.send_requested.connect(self._send)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self._send)
        self.attach_button = QPushButton("Attach")
        self.attach_button.clicked.connect(self.attach_requested.emit)
        self.microphone_button = QPushButton("Mic")
        self.microphone_button.setToolTip("Start or stop voice input")
        self.microphone_button.clicked.connect(self.microphone_requested.emit)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(18, 12, 18, 18)
        input_row.setSpacing(10)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.attach_button)
        input_row.addWidget(self.microphone_button)
        input_row.addWidget(self.send_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll_area, 1)
        layout.addLayout(input_row)

    def set_processing(self, processing: bool) -> None:
        self.input.setDisabled(processing)
        self.send_button.setDisabled(processing)
        self.attach_button.setDisabled(processing)
        self.microphone_button.setDisabled(processing)
        if processing:
            self.show_thinking()
        else:
            self.hide_thinking()

    def add_user_message(self, text: str) -> None:
        self._add_message(ChatMessage("You", text, is_user=True), Qt.AlignmentFlag.AlignRight)

    def add_aura_message(self, text: str) -> None:
        self._add_message(ChatMessage("AURA", text or "I do not have a response for that.", is_user=False), Qt.AlignmentFlag.AlignLeft)

    def set_voice_state(self, label: str, listening: bool = False, busy: bool = False) -> None:
        self.microphone_button.setText(label)
        self.microphone_button.setDisabled(busy)
        self.input.setDisabled(listening or busy)
        self.send_button.setDisabled(listening or busy)
        self.attach_button.setDisabled(listening or busy)
        self.input.setPlaceholderText("Listening..." if listening else "Ask AURA anything...")

    def set_input_text(self, text: str) -> None:
        self.input.setPlainText(text)
        self.input.setFocus()

    def show_thinking(self) -> None:
        if self.thinking_widget is not None:
            return
        label = QLabel("AURA is thinking...")
        label.setObjectName("subtitle")
        self.thinking_widget = label
        self.message_layout.insertWidget(self.message_layout.count() - 1, label, alignment=Qt.AlignmentFlag.AlignLeft)
        self._scroll_to_bottom()

    def hide_thinking(self) -> None:
        if self.thinking_widget is None:
            return
        self.thinking_widget.setParent(None)
        self.thinking_widget.deleteLater()
        self.thinking_widget = None

    def _send(self) -> None:
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.input.clear()
        self.send_requested.emit(text)

    def _add_message(self, widget: ChatMessage, alignment: Qt.AlignmentFlag) -> None:
        self.message_layout.insertWidget(self.message_layout.count() - 1, widget, alignment=alignment)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(0, lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum()))
