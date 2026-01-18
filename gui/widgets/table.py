from pathlib import Path
from typing import cast

from PyQt6.QtCore import Qt, QModelIndex, QSortFilterProxyModel, pyqtSignal
from PyQt6.QtWidgets import QDialog, QWidget, QTreeView, QVBoxLayout

from msc.es2.types import ES2Field

from ..dialogs import EditDialog
from ..models import TreeModel


class TableWidget(QWidget):
    filename: Path
    file_data: dict[str, ES2Field]
    changed: bool = False

    data_changed = pyqtSignal(bool)

    def __init__(self, parent=None, *, filename: Path, data: dict[str, ES2Field]):
        super().__init__(parent)

        self.filename = filename
        self.file_data = data
        self.changed = False

        layout = QVBoxLayout()
        self.tree_view = QTreeView()
        layout.addWidget(self.tree_view)
        self.setLayout(layout)

        self.datamodel = QSortFilterProxyModel()
        self.datamodel.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.datamodel.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self.tree_view.setModel(self.datamodel)

        self.datamodel.setSourceModel(TreeModel(self.file_data))
        self.tree_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.tree_view.resizeColumnToContents(0)

        self.tree_view.doubleClicked.connect(self.treeView_doubleClicked)

    def treeView_doubleClicked(self, index: QModelIndex):
        self.edit_index(index.siblingAtColumn(0))

    def edit_index(self, index: QModelIndex):
        tag = cast(str, index.data())
        dialog = EditDialog(tag, self.file_data[tag], self)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            dialog_result = dialog.get_value()
            if self.file_data[tag].value == dialog_result:
                return
            self.changed = True
            self.data_changed.emit(True)
            self.file_data[tag].value = dialog_result
            value_index = index.siblingAtColumn(2)
            self.datamodel.setData(value_index, dialog_result)
