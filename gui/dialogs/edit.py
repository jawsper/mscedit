from typing import Any

from PyQt5.QtWidgets import QDialog
from PyQt5.uic import loadUi

from msc.es2.types import ES2Field


class EditDialog(QDialog):
    tag: str
    item: Any

    def __init__(self, tag: str, item: ES2Field, parent=None):
        super().__init__(parent)

        self.tag = tag
        self.item = item

        self.ui = loadUi("gui/EditDialog.ui", self)
        self.ui.widget.set_tag(tag)
        self.ui.widget.set_item(item)

    def get_value(self):
        return self.ui.widget.get_value()
