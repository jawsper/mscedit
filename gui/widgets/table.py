from functools import partial
import logging
from pathlib import Path
from typing import cast

from PyQt6.QtCore import (
    Qt,
    QModelIndex,
    QSortFilterProxyModel,
    pyqtSignal,
    QItemSelection,
    QPoint,
)
from PyQt6.QtGui import (
    QGuiApplication,
    QAction,
)
from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QTreeView,
    QVBoxLayout,
    QAbstractItemView,
    QMenu,
)

from msc.es2.enums import ES2ValueType
from msc.es2.types import ES2Field

from ..dialogs import EditDialog
from ..models import TreeModel, TreeItemIndex, TableItem

logger = logging.getLogger(__name__)


class TreeView(QTreeView):
    selection_changed = pyqtSignal(QItemSelection, QItemSelection)

    def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection):
        super().selectionChanged(selected, deselected)
        self.selection_changed.emit(selected, deselected)


class TableWidget(QWidget):
    datamodel: QSortFilterProxyModel
    tree_view: TreeView
    context_menu: QMenu

    filename: Path
    file_data: dict[str, ES2Field]
    changed: bool = False

    data_changed = pyqtSignal(bool)
    tag_selected = pyqtSignal(str)
    tags_selected_changed = pyqtSignal(dict, set)

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
        self.datamodel.setRecursiveFilteringEnabled(True)
        self.datamodel.setAutoAcceptChildRows(True)
        self.datamodel.setSourceModel(TreeModel(self.file_data))

        self.tree_view.setModel(self.datamodel)
        self.tree_view.sortByColumn(
            TreeItemIndex.TAG.value, Qt.SortOrder.AscendingOrder
        )
        self.tree_view.resizeColumnToContents(TreeItemIndex.TAG.value)
        self.tree_view.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.doubleClicked.connect(self.treeView_doubleClicked)
        self.tree_view.customContextMenuRequested.connect(
            self.treeview_contextmenu_requested
        )
        self.tree_view.selection_changed.connect(self.treeview_selection_changed)

        self.context_menu = QMenu(self.tree_view)

    def reload(self, data: dict[str, ES2Field]):
        self.file_data = data
        self.datamodel.setSourceModel(TreeModel(data))

    def treeview_selection_changed(
        self, selected: QItemSelection, deselected: QItemSelection
    ):
        def _selection_to_tags(selection: QItemSelection) -> set[str]:
            indexes = selection.indexes()

            tags = {
                index.siblingAtColumn(TreeItemIndex.TAG.value).data()
                for index in indexes
            }
            return tags

        def _selected_tags_to_dict(selection: set[str]) -> dict[str, ES2Field]:
            return {tag: self.file_data[tag] for tag in selection}

        self.tags_selected_changed.emit(
            _selected_tags_to_dict(_selection_to_tags(selected)),
            _selection_to_tags(deselected),
        )

    def treeView_doubleClicked(self, index: QModelIndex):
        match index.column():
            case TreeItemIndex.TAG.value:
                print("dclicked the tag")
            case TreeItemIndex.VALUE.value:
                self.edit_index(index)

    def treeview_contextmenu_requested(self, point: QPoint):
        index = self.tree_view.indexAt(point)
        global_point = self.tree_view.viewport().mapToGlobal(point)
        match index.column():
            case TreeItemIndex.TYPE.value:
                menu_item1 = QAction("Test", self.context_menu)
                self.context_menu.exec([menu_item1], global_point)
            case TreeItemIndex.VALUE.value:
                action_copy_value = QAction("Copy", self.context_menu)
                action_copy_value.triggered.connect(
                    partial(
                        self.action_copy_value_triggered,
                        index=index,
                    )
                )
                self.context_menu.exec([action_copy_value], global_point)

    def action_copy_value_triggered(self, checked: bool, *, index: QModelIndex):
        clipboard = QGuiApplication.clipboard()
        assert clipboard
        clipboard.setText(index.data(Qt.ItemDataRole.EditRole))

    def edit_index(self, index: QModelIndex):
        tag_index = index.siblingAtColumn(TreeItemIndex.TAG.value)
        tag: str = cast(str, tag_index.data(Qt.ItemDataRole.UserRole))
        display_tag = cast(str, tag_index.data(Qt.ItemDataRole.DisplayRole))

        if tag not in self.file_data:
            return

        dialog = EditDialog(display_tag, self.file_data[tag], self)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            dialog_result = dialog.get_value()
            if self.file_data[tag].value == dialog_result:
                return
            self.changed = True
            self.data_changed.emit(True)
            self.file_data[tag].value = dialog_result
            value_index: QModelIndex = index.siblingAtColumn(TreeItemIndex.VALUE.value)
            self.datamodel.setData(value_index, dialog_result)
