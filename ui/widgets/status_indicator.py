"""Small status indicator widget."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget


class StatusIndicator(QWidget):
    """Displays READY/PROCESSING/ERROR without fake provider claims."""

    def __init__(self) -> None:
        super().__init__()
        self.dot = QLabel()
        self.label = QLabel("READY")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.dot)
        layout.addWidget(self.label)
        self.set_ready()

    def set_ready(self) -> None:
        self._set("READY", "#34d399")

    def set_processing(self) -> None:
        self._set("PROCESSING", "#fbbf24")

    def set_error(self) -> None:
        self._set("ERROR", "#fb7185")

    def _set(self, text: str, color: str) -> None:
        self.dot.setText("●")
        self.dot.setStyleSheet(f"color: {color}; font-size: 16px;")
        self.label.setText(text)
