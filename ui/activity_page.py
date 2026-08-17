"""Activity/debug page for recent AURA processing metadata."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget

from ui.controller.aura_controller import ActivityRecord


class ActivityPage(QWidget):
    """Displays recent router metadata without sensitive payloads."""

    def __init__(self) -> None:
        super().__init__()
        title = QLabel("Activity")
        title.setObjectName("title")

        self.container = QWidget()
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setContentsMargins(18, 18, 18, 18)
        self.list_layout.setSpacing(12)
        self.list_layout.addWidget(title)
        self.list_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.container)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def refresh(self, activities: list[ActivityRecord]) -> None:
        while self.list_layout.count() > 2:
            item = self.list_layout.takeAt(1)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not activities:
            self.list_layout.insertWidget(1, QLabel("No activity yet."))
            return

        for activity in activities:
            self.list_layout.insertWidget(1, self._card(activity))

    @staticmethod
    def _card(activity: ActivityRecord) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(5)
        values = [
            ("Intent", activity.intent),
            ("Execution Source", activity.execution_source),
            ("LLM", activity.llm_provider),
            ("Model", activity.model),
            ("Execution Time", f"{activity.execution_time:.2f} sec"),
            ("Status", "Success" if activity.success else "Error"),
        ]
        if activity.error:
            values.append(("Error", activity.error))
        for label, value in values:
            line = QLabel(f"{label}: {value or 'Unknown'}")
            line.setWordWrap(True)
            layout.addWidget(line)
        return card
