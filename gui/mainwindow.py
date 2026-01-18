from functools import partial
import logging
import os
import shutil
import sys
import tempfile
from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QApplication,
    QFileDialog,
    QTabWidget,
)
from PyQt6.uic.load_ui import loadUi

from msc.es2 import ES2Reader, ES2Writer
from msc.es2.reader import ES2Field

from .dialogs import BoltCheckerDialog, ErrorDialog, MapViewDialog
from .widgets.table import TableWidget

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _copy_file(src, dst):
    shutil.copyfile(src, dst)
    try:
        shutil.copystat(src, dst)
    except OSError:
        logger.exception("Cannot copy stat")
    try:
        shutil.copymode(src, dst)
    except OSError:
        logger.exception("Cannot copy mode")


class MainWindow(QMainWindow):
    open_file_dir: str
    open_files: set[str]

    def __init__(self):
        super().__init__()

        self.open_file_dir = "."  # os.path.expanduser("~")
        match sys.platform:
            case "win32":
                self.open_file_dir = os.path.expandvars(
                    "%APPDATA%/../LocalLow/Amistech/My Winter Car"
                )
            case "darwin":
                pass
            case "linux":
                pass
            case _:
                pass
        self.open_files = set()

        self.ui = loadUi("gui/MainWindow.ui", self)
        assert self.ui

        self.ui.action_Open.triggered.connect(self.menu_open)
        self.ui.action_Save.triggered.connect(self.menu_save)
        self.ui.action_Close.triggered.connect(self.menu_close)
        self.ui.action_Exit.triggered.connect(QApplication.quit)
        self.ui.action_CaseSensitive.triggered.connect(self.menu_search_mode)

        self.ui.action_ShowMap.triggered.connect(self.show_map)
        self.ui.action_BoltChecker.triggered.connect(self.show_boltchecker)

        tab_widget = cast(QTabWidget, self.ui.tabWidget)
        tab_widget.setTabsClosable(True)
        tab_widget.currentChanged.connect(self.current_tab_changed)
        tab_widget.tabCloseRequested.connect(self.tab_close_requested)

        self.ui.searchField.textChanged.connect(self.searchField_textChanged)

    def menu_open(self):
        """
        Slot that gets triggered by the "Open" menu item.
        """
        filenames, _ = QFileDialog.getOpenFileNames(self, "Open files", self.open_file_dir, filter="TXT-files (*.txt);;All files (*.*)")
        for filename in filenames:
            self.open_file(filename)

    def open_file(self, filename: str):
        if filename in self.open_files:
            return

        self.open_file_dir = os.path.dirname(filename)
        try:
            with open(filename, "rb") as f:
                reader = ES2Reader(f)
                file_data = reader.read_all()
        except Exception as e:
            logger.exception("Failed to load file")
            return self.show_error(e)

        self.open_files.add(filename)

        self.open_new_tab(filename, file_data)

    def open_new_tab(self, filename: str, file_data: dict[str, ES2Field]):
        tab_widget = cast(QTabWidget, self.ui.tabWidget)
        table_widget = TableWidget(filename=filename, data=file_data)
        index = tab_widget.addTab(table_widget, os.path.basename(filename))
        table_widget.data_changed.connect(
            partial(self.set_data_changed, filename=filename, tab_index=index)
        )
        table_widget.datamodel.setFilterWildcard(self.ui.searchField.text())
        table_widget.datamodel.setFilterCaseSensitivity(
            Qt.CaseSensitivity.CaseSensitive
            if self.ui.action_CaseSensitive.isChecked()
            else Qt.CaseSensitivity.CaseInsensitive
        )
        tab_widget.setCurrentIndex(index)

    def current_tab_changed(self, index: int):
        """
        Slot that gets triggered when the tabWidget changed tabs.
        """
        tab = cast(TableWidget | None, self.ui.tabWidget.widget(index))
        if tab:
            self.ui.action_Save.setEnabled(tab.changed)
            self.ui.action_Close.setEnabled(True)
        else:
            self.ui.action_Save.setEnabled(False)
            self.ui.action_Close.setEnabled(False)

    def tab_close_requested(self, index: int):
        """
        Slot that gets triggered by the tab close button pressed on a tab in the tabWidget
        """
        self._close_tab_by_index(index)

    def set_data_changed(
        self, changed: bool = True, *, filename: str = "", tab_index: int = -1
    ):
        """
        Slot that gets triggered when the data_changed signal on a TableWidget gets triggered.
        """
        logger.info("CHANGED %s %d %d", filename, tab_index, changed)
        tab_widget = cast(QTabWidget, self.ui.tabWidget)
        tab_widget.setTabText(
            tab_index, f"{os.path.basename(filename)}{' *' if changed else ''}"
        )

        self.ui.action_Save.setEnabled(changed)

    def menu_save(self):
        """
        Slot that gets triggered by the "Save" menu item.
        """
        index = self._current_tab_index()
        tab = self._current_tab()
        if tab is None:
            return
        assert tab.filename
        assert tab.file_data
        for i in range(100):
            backup_filename = f"{tab.filename}.{i}"
            if not os.path.exists(backup_filename):
                _copy_file(tab.filename, backup_filename)
                break
        else:
            raise Exception("Too many backups!")

        with tempfile.NamedTemporaryFile("wb", delete_on_close=False) as f:
            writer = ES2Writer(f.file)
            for k, v in tab.file_data.items():
                writer.save(k, v)
            writer.save_all()

            f.close()

            _copy_file(f.name, tab.filename)

        self.set_data_changed(False, filename=tab.filename, tab_index=index)

    def menu_close(self):
        """
        Slot that gets triggered by the "Close" menu item.
        """
        index = cast(QTabWidget, self.ui.tabWidget).currentIndex()
        self._close_tab_by_index(index)

    def _close_tab_by_index(self, index: int):
        tab_widget = cast(QTabWidget, self.ui.tabWidget)
        tab = cast(TableWidget | None, tab_widget.widget(index))
        if tab:
            self.open_files.remove(tab.filename)
        tab_widget.removeTab(index)

    def menu_search_mode(self, action: bool):
        """
        Slot that gets triggered by the action_CaseSensitivity action in the menuSearch_mode menu item.
        """
        for tab in self._all_tabs():
            tab.datamodel.setFilterCaseSensitivity(
                Qt.CaseSensitivity.CaseSensitive
                if action
                else Qt.CaseSensitivity.CaseInsensitive
            )

    def searchField_textChanged(self, text: str):
        """
        Slot that gets triggered by the textChanged signal of searchField.
        """
        for tab in self._all_tabs():
            tab.datamodel.setFilterWildcard(text)

    def show_map(self):
        """
        Slot that gets triggered by the "Show map" menu item.
        """
        tab = self._current_tab()
        if tab:
            dialog = MapViewDialog(tab.file_data, self)
            dialog.exec()

    def show_boltchecker(self):
        """
        Slot that gets triggered by the "Boltchecker" menu item.
        """
        tab = self._current_tab()
        if tab:
            dialog = BoltCheckerDialog(tab.file_data, self)
            dialog.exec()

    def show_error(self, exception: Exception):
        """
        Helper function to display exceptions.
        """
        dialog = ErrorDialog(exception, self)
        dialog.exec()

    def _current_tab_index(self) -> int:
        """
        Helper to get the index of the currently selected tab, or -1 if no tabs.
        """
        tab_widget = cast(QTabWidget, self.ui.tabWidget)
        return tab_widget.currentIndex()

    def _current_tab(self) -> TableWidget | None:
        """
        Helper to get the TableWidget of the currently selected tab, or None if no tabs.
        """
        tab_widget = cast(QTabWidget, self.ui.tabWidget)
        return cast(TableWidget | None, tab_widget.currentWidget())

    def _all_tabs(self) -> list[TableWidget]:
        """
        Helper function to get all TableWidgets of all tabs.
        """
        tab_widget = cast(QTabWidget, self.ui.tabWidget)
        tabs = []
        for index in range(tab_widget.count()):
            tabs.append(tab_widget.widget(index))
        return tabs
