#!/usr/bin/python3

import logging
import sys

from PyQt6.QtWidgets import QApplication

from gui.windows.main import MainWindow


logging.basicConfig()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
