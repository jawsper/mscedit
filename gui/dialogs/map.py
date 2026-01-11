from itertools import cycle

from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QDialog, QGraphicsScene, QGraphicsView, QVBoxLayout, QWidget
from PyQt6.QtGui import QPixmap, QPainter, QPen
from PyQt6.uic.load_ui import loadUi

from msc.es2.enums import ES2ValueType
from msc.es2.types import ES2Field


class MapWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.background = QPixmap("gui/perjarvi_road_map.png")
        self.markers = {}
        self.setFixedSize(self.background.size())

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.drawPixmap(0, 0, self.background)

        point = QPoint()
        pen = QPen(Qt.GlobalColor.red)
        pen.setWidth(10)
        colors = cycle(
            [
                Qt.GlobalColor.magenta,
                Qt.GlobalColor.red,
                Qt.GlobalColor.blue,
                Qt.GlobalColor.green,
                Qt.GlobalColor.yellow,
                Qt.GlobalColor.cyan,
            ]
        )
        for marker in self.markers.values():
            pen.setColor(next(colors))
            qp.setPen(pen)
            point.setX(marker[0])
            point.setY(marker[1])
            qp.drawPoint(point)

    def add_marker(self, tag: str, x_pos: float, y_pos: float):
        if tag in self.markers:
            return

        def scale_value(old_value, old_min, old_max, new_min, new_max):
            return (
                (new_max - new_min) * (old_value - old_min) / (old_max - old_min)
            ) + new_min

        raw_x, raw_z = x_pos, y_pos
        x_range = -1851, 2334
        y_range = 1823, -1548
        x = scale_value(raw_x, x_range[0], x_range[1], 0, self.background.width())
        y = scale_value(raw_z, y_range[0], y_range[1], 0, self.background.height())
        self.markers[tag] = (int(x), int(y))
        self.update()

    def clear_markers(self):
        self.markers = {}
        self.update()


class MapViewDialog(QDialog):
    factor = 1.5

    def __init__(self, model: dict[str, ES2Field], parent=None):
        super().__init__(parent)

        self.model = model

        self.ui = loadUi("gui/MapViewDialog.ui", self)
        assert self.ui
        self.ui.addItemButton.clicked.connect(self.button_add_clicked)
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

        layout: QVBoxLayout = self.ui.verticalLayout
        layout.insertWidget(1, self._view)

        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.ZoomIn),
            self._view,
            context=QtCore.Qt.ShortcutContext.WidgetShortcut,
            activated=self.zoom_in,
        )

        QtGui.QShortcut(
            QtGui.QKeySequence(QtGui.QKeySequence.StandardKey.ZoomOut),
            self._view,
            context=QtCore.Qt.ShortcutContext.WidgetShortcut,
            activated=self.zoom_out,
        )

    @QtCore.pyqtSlot()
    def zoom_in(self):
        scale_tr = QtGui.QTransform()
        scale_tr.scale(MapViewDialog.factor, MapViewDialog.factor)

        tr = self._view.transform() * scale_tr
        self._view.setTransform(tr)

    @QtCore.pyqtSlot()
    def zoom_out(self):
        scale_tr = QtGui.QTransform()
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

    def button_clear_clicked(self):
        self._map.clear_markers()
