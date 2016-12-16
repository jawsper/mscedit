#!/usr/bin/python3

import os

from PyQt5.QtWidgets import QApplication

from gui import MainWindow


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    # window.open_file(os.path.expanduser('~/appdata/locallow/amistech/My Summer Car/defaultES2File.txt'))
    window.open_file(os.path.expanduser('~/sync/Amistech/My Summer Car/defaultES2File.txt'))
    sys.exit(app.exec_())
