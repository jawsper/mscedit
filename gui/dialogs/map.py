from itertools import cycle

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QDialog
from PyQt5.QtGui import QPixmap, QPainter, QPen
from PyQt5.uic import loadUi

from msc.es2 import ES2ValueType


class MapViewDialog(QDialog):
    def __init__(self, model, parent=None):
        super().__init__(parent)

        self.model = model

        self.ui = loadUi("gui/MapViewDialog.ui", self)
        assert self.ui
        self.ui.addItemButton.clicked.connect(self.button_add_clicked)
        self.ui.clearButton.clicked.connect(self.button_clear_clicked)

        transform_tags = []
        for tag, item in self.model.items():
            if item.header.value_type == ES2ValueType.transform:
                transform_tags.append(tag)

        for tag in sorted(transform_tags):
            self.ui.selectionBox.addItem(tag)

        self.background = QPixmap("gui/perjarvi_road_map.png")
        self.ui.map.setPixmap(self.background)
        self.ui.map.mousePressed.connect(self.map_mouse_pressed)
        self.markers = []

    def button_add_clicked(self):
        tag = self.ui.selectionBox.currentText()
        item = self.model[tag]
        if item.header.value_type != ES2ValueType.transform:
            return
        position = item.value.position
        self.add_marker(position.x, position.z)
        self.draw_markers()

    def button_clear_clicked(self):
        self.markers = []
        self.draw_markers()

    def map_mouse_pressed(self, event):
        print("map_mouse_pressed")
        print(event.localPos())

    def draw_markers(self):
        pixmap = self.background.copy()
        image = pixmap.toImage()
        painter = QPainter()
        painter.begin(image)
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
        for marker in self.markers:
            pen.setColor(next(colors))
            painter.setPen(pen)
            point.setX(marker[0])
            point.setY(marker[1])
            painter.drawPoint(point)
        painter.end()
        self.ui.map.setPixmap(QPixmap.fromImage(image))

    def add_marker(self, x_pos, y_pos):
        def scale_value(old_value, old_min, old_max, new_min, new_max):
            return (
                (new_max - new_min) * (old_value - old_min) / (old_max - old_min)
            ) + new_min

        def remap(value, old_min, old_max):
            return scale_value(value, old_min, old_max, 0, 1024)

        raw_x, raw_z = x_pos, y_pos
        x_range = -1851, 2334
        y_range = 1823, -1548
        x = scale_value(raw_x, x_range[0], x_range[1], 0, self.background.width())
        y = scale_value(raw_z, y_range[0], y_range[1], 0, self.background.height())
        self.markers.append((int(x), int(y)))
