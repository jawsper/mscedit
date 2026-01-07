from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox


class ErrorDialog(QDialog):
    def __init__(self, exception: Exception, parent=None):
        super().__init__(parent)

        self.setWindowTitle("An error has occured.")

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.accepted.connect(self.accept)

        layout = QVBoxLayout()
        label = QLabel(str(exception))
        layout.addWidget(label)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
