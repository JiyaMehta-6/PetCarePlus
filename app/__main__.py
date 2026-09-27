"""Launch the PetCare+ desktop application.

Works both as ``python -m app`` and ``python app/__main__.py`` by ensuring the
project root (the parent of this file's directory) is on ``sys.path``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is importable when run as a plain script.
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from app.ui.main_window import MainWindow
from app.ui.components.icons import logo_icon
from app.log_utils import setup_logging, get_logger

logger = get_logger("petcare")


def main() -> int:
    setup_logging()
    app = QApplication(sys.argv)
    # Explicit font avoids Qt's "point size <= 0" warning from the default font.
    app.setFont(QFont("Segoe UI", 10))
    app.setApplicationName("PetCare+")
    app.setWindowIcon(logo_icon(64))
    window = MainWindow()
    window.show()
    logger.info("PetCare+ UI started")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
