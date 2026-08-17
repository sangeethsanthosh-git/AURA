"""Settings foundation for AURA Desktop."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QFrame, QLabel, QVBoxLayout, QWidget


class SettingsPage(QWidget):
    """Safe settings surface that does not expose secrets."""

    tts_changed = pyqtSignal(bool)

    def __init__(self) -> None:
        super().__init__()
        title = QLabel("Settings")
        title.setObjectName("title")

        self.tts_checkbox = QCheckBox("TTS Enabled")
        self.tts_checkbox.toggled.connect(self.tts_changed.emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(self._section("General", ["Theme: Dark"]))
        layout.addWidget(self._section("AI / Models", ["Providers use existing environment configuration.", "API keys are not shown."]))
        voice = QFrame()
        voice.setObjectName("card")
        voice_layout = QVBoxLayout(voice)
        voice_layout.addWidget(QLabel("Voice"))
        voice_layout.addWidget(self.tts_checkbox)
        layout.addWidget(voice)
        layout.addWidget(self._section("System", ["AURA ASUS V1", "Status: Ready"]))
        layout.addStretch()

    @staticmethod
    def _section(title: str, lines: list[str]) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        heading = QLabel(title)
        heading.setObjectName("messageAuthor")
        layout.addWidget(heading)
        for line in lines:
            label = QLabel(line)
            label.setWordWrap(True)
            layout.addWidget(label)
        return card
