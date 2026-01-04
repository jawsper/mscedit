import logging
import os
import shutil
import tempfile
from typing import cast

from PyQt5.QtCore import Qt, QModelIndex, QSortFilterProxyModel
from PyQt5.QtWidgets import QMainWindow, qApp, QFileDialog, QDialog
from PyQt5.uic import loadUi

from msc.es2 import ES2Reader, ES2Writer
from msc.es2.reader import ES2Field
from gui.models import TreeModel

from .dialogs import BoltCheckerDialog, EditDialog, ErrorDialog, MapViewDialog


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    file_data: dict[str, ES2Field]

    def __init__(self):
        super().__init__()

        self.filename = None
        self.data_changed = False
        self.file_data = None

        self.open_file_dir = os.path.expanduser("~")

        self.ui = loadUi("gui/MainWindow.ui", self)
        assert self.ui

        self.ui.action_Open.triggered.connect(self.menu_open)
        self.ui.action_Save.triggered.connect(self.menu_save)
        self.ui.action_Close.triggered.connect(self.menu_close)
        self.ui.action_Exit.triggered.connect(qApp.quit)

        self.ui.action_ShowMap.triggered.connect(self.show_map)
        self.ui.action_BoltChecker.triggered.connect(self.show_boltchecker)

        self.datamodel = QSortFilterProxyModel()
        self.datamodel.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.datamodel.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.ui.treeView.setSortingEnabled(False)
        self.ui.treeView.setModel(self.datamodel)
        self.ui.treeView.setSortingEnabled(True)

        self.ui.treeView.doubleClicked.connect(self.treeView_doubleClicked)
        self.ui.treeView.selectionModel().selectionChanged.connect(
            self.treeView_selectionChanged
        )
        self.ui.searchField.textChanged.connect(self.searchField_textChanged)

    def menu_open(self):
        fname = QFileDialog.getOpenFileName(self, "Open file", self.open_file_dir)
        if fname[0]:
            self.open_file(fname[0])

    def open_file(self, filename: str):
        self.filename = filename
        self.open_file_dir = os.path.dirname(self.filename)
        try:
            with open(filename, "rb") as f:
                reader = ES2Reader(f)
                self.file_data = reader.read_all()
        except Exception as e:
            logger.exception("Failed to load file")
            return self.show_error(e)
        self.update_tree(self.file_data)
        self.set_changed(False)
        self.ui.action_Close.setEnabled(True)

    def set_changed(self, changed: bool = True):
        self.data_changed = changed
        self.ui.action_Save.setEnabled(self.data_changed)

    def menu_save(self):
        assert self.filename
        assert self.file_data
        for i in range(100):
            backup_filename = f"{self.filename}.{i}"
            if not os.path.exists(backup_filename):
                shutil.copy2(self.filename, backup_filename)
                break
        else:
            raise Exception("Too many backups!")

        with tempfile.NamedTemporaryFile("wb") as f:
            writer = ES2Writer(f)
            for k, v in self.file_data.items():
                writer.save(k, v)
            writer.save_all()

            shutil.copy2(f.name, self.filename)

        self.set_changed(False)

    def menu_close(self):
        assert self.ui
        self.ui.action_Save.setEnabled(False)
        self.ui.action_Close.setEnabled(False)
        self.filename = None
        self.file_data = None
        self.update_tree(None)

    def update_tree(self, file_data=None):
        assert self.ui
        self.datamodel.setSourceModel(TreeModel(file_data))
        self.ui.treeView.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.ui.treeView.resizeColumnToContents(0)

    def treeView_selectionChanged(self):
        pass
        # indexes = self.ui.treeView.selectionModel().selection().indexes()
        # if len(indexes) > 0:
        #     index = indexes[0]
        #     tag = self.datamodel.data(index)
        #     print('selectionChanged')
        #     print(self.file_data[item].header.value_type)
        #     print(self.file_data[item].value)

    def treeView_doubleClicked(self):
        assert self.ui
        index: QModelIndex = self.ui.treeView.selectionModel().selection().indexes()[0]
        self.edit_index(index)

    def edit_index(self, index: QModelIndex):
        assert self.ui
        assert self.file_data
        tag = cast(str, index.data())
        dialog = EditDialog(tag, self.file_data[tag], self)
        result = dialog.exec_()
        if result == QDialog.DialogCode.Accepted:
            dialog_result = dialog.get_value()
            if self.file_data[tag].value == dialog_result:
                return
            self.set_changed()
            self.file_data[tag].value = dialog_result
            value_index = self.datamodel.index(index.row(), 2)
            self.datamodel.setData(value_index, dialog_result)

    def searchField_textChanged(self, text: str):
        self.datamodel.setFilterWildcard(text)

    def show_map(self):
        dialog = MapViewDialog(self.file_data, self)
        dialog.exec_()

    def show_boltchecker(self):
        dialog = BoltCheckerDialog(self.file_data, self)
        dialog.exec_()

    def show_error(self, exception: Exception):
        dialog = ErrorDialog(exception, self)
        dialog.exec_()
