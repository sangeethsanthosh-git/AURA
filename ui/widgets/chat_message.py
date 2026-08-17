"""Chat message bubble widget."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout


class ChatMessage(QFrame):
    """Simple message bubble for user and AURA messages."""

    def __init__(self, author: str, text: str, is_user: bool = False) -> None:
        super().__init__()
        self.setObjectName("userMessage" if is_user else "auraMessage")
        self.setMaximumWidth(760)

        author_label = QLabel(f"{author} · {datetime.now().strftime('%H:%M')}")
        author_label.setObjectName("messageAuthor")

        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setObjectName("messageBody")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(6)
        layout.addWidget(author_label)
        layout.addWidget(body)
