from PyQt5.QtWidgets import QDialog
from PyQt5.uic import loadUi


class EditDialog(QDialog):
    def __init__(self, tag, item, parent=None):
        super().__init__(parent)

        self.tag = tag
        self.item = item

        self.ui = loadUi("gui/EditDialog.ui", self)
        self.ui.widget.set_tag(tag)
        self.ui.widget.set_item(item)

    def get_value(self):
        return self.ui.widget.get_value()
