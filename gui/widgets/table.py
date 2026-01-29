from pathlib import Path
from typing import cast

from PyQt6.QtCore import Qt, QModelIndex, QSortFilterProxyModel, pyqtSignal
from PyQt6.QtWidgets import QDialog, QWidget, QTreeView, QVBoxLayout

from msc.es2.types import ES2Field

from ..dialogs import EditDialog
from ..models import TreeModel


class TreeView(QTreeView):
    current_changed = pyqtSignal(QModelIndex, QModelIndex)

    def currentChanged(self, current: QModelIndex, previous: QModelIndex):
        super().currentChanged(current, previous)
        self.current_changed.emit(current, previous)


class TableWidget(QWidget):
    filename: Path
    file_data: dict[str, ES2Field]
    changed: bool = False

    data_changed = pyqtSignal(bool)
    tag_selected = pyqtSignal(str)

    def __init__(self, parent=None, *, filename: Path, data: dict[str, ES2Field]):
        super().__init__(parent)

        self.filename = filename
        self.file_data = data
        self.changed = False

        layout = QVBoxLayout()
        self.tree_view = TreeView()
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
        self.tree_view.current_changed.connect(self.treeview_current_changed)

    def reload(self, data: dict[str, ES2Field]):
        self.file_data = data
        self.datamodel.setSourceModel(TreeModel(data))

    def treeview_current_changed(self, current: QModelIndex, previous: QModelIndex):
        if current.isValid():
            tag_index = current.siblingAtColumn(0)
            tag: str = cast(str, tag_index.data())
            self.tag_selected.emit(tag)

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
