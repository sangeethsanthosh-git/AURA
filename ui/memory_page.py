"""Memory review page."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget


class MemoryPage(QWidget):
    """Displays stored memories and forgets through backend logic."""

    refresh_requested = pyqtSignal()
    forget_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        title = QLabel("Memory")
        title.setObjectName("title")
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh_requested.emit)

        self.container = QWidget()
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setContentsMargins(18, 18, 18, 18)
        self.list_layout.setSpacing(12)
        self.list_layout.addWidget(title)
        self.list_layout.addWidget(refresh)
        self.list_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.container)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def refresh_memories(self, memories: list[dict[str, object]]) -> None:
        while self.list_layout.count() > 3:
            item = self.list_layout.takeAt(2)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not memories:
            self.list_layout.insertWidget(2, QLabel("No active memories yet."))
            return

        for memory in memories:
            self.list_layout.insertWidget(2, self._card(memory))

    def _card(self, memory: dict[str, object]) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        category = QLabel(str(memory.get("category", "CUSTOM")))
        category.setObjectName("messageAuthor")
        content = QLabel(str(memory.get("content", "")))
        content.setWordWrap(True)
        status = QLabel(f"Status: {memory.get('status', 'Unknown')}")
        forget = QPushButton("Forget")
        forget.clicked.connect(lambda: self.forget_requested.emit(str(memory.get("content", ""))))
        layout.addWidget(category)
        layout.addWidget(content)
        layout.addWidget(status)
        layout.addWidget(forget)
        return card
