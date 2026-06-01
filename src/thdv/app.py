from __future__ import annotations

import signal
import sys

from PySide6.QtWidgets import QApplication

from .windows import MainWindow


def main() -> int:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
