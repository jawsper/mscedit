from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QGraphicsScene, QGraphicsView, QVBoxLayout
from PyQt6.QtGui import (
    QKeySequence,
    QShortcut,
    QTransform,
)
from PyQt6.uic.load_ui import loadUi

from gui.widgets.map import MapWidget
from msc.es2.enums import ES2ValueType
from msc.es2.types import ES2Field


class MapViewDialog(QDialog):
    factor = 1.5
    _scene: QGraphicsScene
    _view: QGraphicsView

    def __init__(self, model: dict[str, ES2Field], parent=None):
        super().__init__(parent)

        self.model = model

        self.ui = loadUi("gui/MapViewDialog.ui", self)
        assert self.ui
        self.ui.addItemButton.clicked.connect(self.button_add_clicked)
        self.ui.addAllItemsButton.clicked.connect(self.button_add_all_clicked)
        self.ui.clearButton.clicked.connect(self.button_clear_clicked)
        self.ui.zoomInButton.clicked.connect(self.zoom_in)
        self.ui.zoomOutButton.clicked.connect(self.zoom_out)

        transform_tags = []
        for tag, item in self.model.items():
            if item.header.value_type == ES2ValueType.transform:
                transform_tags.append(tag)

        for tag in sorted(transform_tags, key=lambda v: v.lower()):
            self.ui.selectionBox.addItem(tag)

        self._scene = QGraphicsScene(self)
        self._view = QGraphicsView(self._scene)

        self._map = MapWidget()
        self._scene.addWidget(self._map)

        self._view.fitInView(
            self._scene.itemsBoundingRect(),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

        layout: QVBoxLayout = self.ui.verticalLayout
        layout.insertWidget(1, self._view)

        QShortcut(
            QKeySequence(QKeySequence.StandardKey.ZoomIn),
            self._view,
            context=Qt.ShortcutContext.WidgetShortcut,
            activated=self.zoom_in,
        )

        QShortcut(
            QKeySequence(QKeySequence.StandardKey.ZoomOut),
            self._view,
            context=Qt.ShortcutContext.WidgetShortcut,
            activated=self.zoom_out,
        )

    @pyqtSlot()
    def zoom_in(self):
        scale_tr = QTransform()
        scale_tr.scale(MapViewDialog.factor, MapViewDialog.factor)

        tr = self._view.transform() * scale_tr
        self._view.setTransform(tr)

    @pyqtSlot()
    def zoom_out(self):
        scale_tr = QTransform()
        scale_tr.scale(MapViewDialog.factor, MapViewDialog.factor)

        scale_inverted, invertible = scale_tr.inverted()

        if invertible:
            tr = self._view.transform() * scale_inverted
            self._view.setTransform(tr)

    def button_add_clicked(self):
        tag = self.ui.selectionBox.currentText()
        item = self.model[tag]
        if item.header.value_type != ES2ValueType.transform:
            return
        position = item.value.position
        self._map.add_marker(tag, position.x, position.z)

    def button_add_all_clicked(self):
        for tag, item in self.model.items():
            if item.header.value_type != ES2ValueType.transform:
                continue
            position = item.value.position
            self._map.add_marker(tag, position.x, position.z)

    def button_clear_clicked(self):
        self._map.clear_markers()
