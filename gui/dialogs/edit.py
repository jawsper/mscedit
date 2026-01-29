from typing import Any, cast

from PyQt6.QtWidgets import QDialog
from PyQt6.uic.load_ui import loadUi

from msc.es2.types import ES2Field

from gui.widgets.edit import EditWidget


class EditDialog(QDialog):
    tag: str
    item: Any

    def __init__(self, tag: str, item: ES2Field, parent=None):
        super().__init__(parent)

        self.tag = tag
        self.item = item

        self.ui = loadUi("gui/EditDialog.ui", self)
        self.widget = EditWidget(tag=tag, item=item)
        self.ui.verticalLayout.insertWidget(0, self.widget)

    def get_value(self):
        return self.widget.get_value()
