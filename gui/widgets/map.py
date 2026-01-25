from itertools import cycle

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import (
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
)


class MapWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.background = QPixmap("gui/perjarvi_road_map.png")
        self.markers = {}
        self.setFixedSize(self.background.size())

    def paintEvent(self, event: QPaintEvent):
        qp = QPainter(self)
        qp.drawPixmap(0, 0, self.background)

        point = QPoint()
        text_offset = QPoint()
        text_offset.setX(5)
        text_offset.setY(5)
        pen = QPen(Qt.GlobalColor.red)
        pen.setWidth(5)
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
        for tag, marker in self.markers.items():
            pen.setColor(next(colors))
            qp.setPen(pen)
            point.setX(marker[0])
            point.setY(marker[1])
            qp.drawPoint(point)
            qp.drawText(point + text_offset, tag)

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
