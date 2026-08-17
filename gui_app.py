"""PyQt6 launcher for AURA Desktop UI."""

from __future__ import annotations

import logging
import sys

from PyQt6.QtWidgets import QApplication

from app import configure_console_encoding
from ui.main_window import MainWindow


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    configure_console_encoding()
    app = QApplication(sys.argv)
    app.setApplicationName("AURA ASUS")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
