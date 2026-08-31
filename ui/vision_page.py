"""PyQt Vision status page for AURA Eyes."""

from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class VisionPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        title = QLabel("AURA EYES")
        title.setObjectName("title")
        self.state = QLabel("EYES OFF")
        self.details = QLabel("")
        self.details.setWordWrap(True)
        self.action_hint = QLabel("Use chat actions: Look at Screen, Read Screen, Describe Screen, Verify Screen.")
        self.action_hint.setWordWrap(True)
        self.refresh_button = QPushButton("Refresh Vision Status")

        layout.addWidget(title)
        layout.addWidget(self.state)
        layout.addWidget(self.details)
        layout.addWidget(self.action_hint)
        layout.addWidget(self.refresh_button)
        layout.addStretch()

    def refresh_status(self, status: dict[str, Any]) -> None:
        state = str(status.get("state", "UNAVAILABLE"))
        self.state.setText(f"EYES {state}")
        languages = ", ".join(str(item) for item in status.get("languages", [])) or "None"
        self.details.setText(
            "\n".join(
                [
                    f"OCR: {'Available' if status.get('ocr_available') else 'Unavailable'}",
                    f"Vision: {'Available' if status.get('vision_available') else 'Unavailable'}",
                    f"Active window: {'Available' if status.get('active_window_inspection') else 'Unavailable'}",
                    f"Continuous capture: {'On' if status.get('continuous_capture') else 'Off'}",
                    f"OCR provider: {status.get('ocr_provider') or 'None'}",
                    f"Vision provider: {status.get('vision_provider') or 'None'}",
                    f"Languages: {languages}",
                    f"Model policy: {status.get('model_policy', 'UNLOAD_AFTER_TASK')}",
                ]
            )
        )

