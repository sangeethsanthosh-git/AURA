"""PySide6 + QML launcher for the official AURA ASUS desktop UI."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from app import configure_console_encoding
from ui.bridge.aura_bridge import AuraBridge


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    configure_console_encoding()
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication(sys.argv)
    app.setApplicationName("AURA ASUS")
    app.setOrganizationName("AURA")

    engine = QQmlApplicationEngine()
    bridge = AuraBridge()
    engine.rootContext().setContextProperty("auraBridge", bridge)

    qml_path = Path(__file__).resolve().parent / "ui" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1

    bridge.initializeBackend()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
