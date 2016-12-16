import os

from PyQt5.QtCore import (Qt, QSortFilterProxyModel)
from PyQt5.QtWidgets import (QMainWindow, qApp,
    QFileDialog, QDialog)
from PyQt5.uic import loadUi

from msc import ES2Reader, ES2Writer
from gui.models import TreeModel


class EditDialog(QDialog):
    def __init__(self, tag, item, parent=None):
        super().__init__(parent)

        self.tag = tag
        self.item = item

        self.ui = loadUi('gui/EditDialog.ui', self)
        self.ui.widget.set_tag(tag)
        self.ui.widget.set_item(item)

    def get_value(self):
        return self.ui.widget.get_value()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.filename = None
        self.file_data = None

        self.open_file_dir = os.path.expanduser('~')

        self.ui = loadUi('gui/MainWindow.ui', self)

        self.ui.action_Open.triggered.connect(self.menu_open)
        self.ui.action_Save.triggered.connect(self.menu_save)
        self.ui.action_Close.triggered.connect(self.menu_close)
        self.ui.action_Exit.triggered.connect(qApp.quit)

        self.datamodel = QSortFilterProxyModel()
        self.datamodel.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.datamodel.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.ui.treeView.setSortingEnabled(False)
        self.ui.treeView.setModel(self.datamodel)
        self.ui.treeView.setSortingEnabled(True)

        self.ui.treeView.doubleClicked.connect(self.treeView_doubleClicked)
        self.ui.treeView.selectionModel().selectionChanged.connect(self.treeView_selectionChanged)
        self.ui.searchField.textChanged.connect(self.searchField_textChanged)

    def menu_open(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', self.open_file_dir)
        if fname[0]:
            self.open_file(fname[0])

    def open_file(self, filename):
        self.filename = filename
        self.open_file_dir = os.path.dirname(self.filename)
        with open(filename, 'rb') as f:
            reader = ES2Reader(f)
            self.file_data = reader.read_all()
        self.update_tree(self.file_data)
        self.ui.action_Save.setEnabled(True)
        self.ui.action_Close.setEnabled(True)

    def menu_save(self):
        with open(self.filename + '.out', 'wb') as f:
            writer = ES2Writer(f)
            for k, v in self.file_data.items():
                writer.save(k, v)
            writer.save_all()


    def menu_close(self):
        self.ui.action_Save.setEnabled(False)
        self.ui.action_Close.setEnabled(False)
        self.filename = None
        self.file_data = None
        self.update_tree(None)

    def update_tree(self, file_data=None):
        self.datamodel.setSourceModel(TreeModel(file_data))
        self.ui.treeView.sortByColumn(0, Qt.AscendingOrder)
        self.ui.treeView.resizeColumnToContents(0)

    def treeView_selectionChanged(self):
        indexes = self.ui.treeView.selectionModel().selection().indexes()
        if len(indexes) > 0:
            index = indexes[0]
            tag = self.datamodel.data(index)

            # print('selectionChanged')
            # print(self.file_data[item].header.value_type)
            # print(self.file_data[item].value)

    def treeView_doubleClicked(self):
        index = self.ui.treeView.selectionModel().selection().indexes()[0]
        self.edit_index(index)

    def edit_index(self, index):
        tag = index.data()
        dialog = EditDialog(tag, self.file_data[tag], self)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            self.file_data[tag].value = value = dialog.get_value()
            value_index = self.datamodel.index(index.row(), 2)
            self.datamodel.setData(value_index, value)

    def searchField_textChanged(self, text):
        self.datamodel.setFilterWildcard(text)

