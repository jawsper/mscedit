from itertools import cycle
import logging
from pathlib import Path

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtWidgets import (
    QDockWidget,
    QGraphicsScene,
    QGraphicsView,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QPixmap, QTransform, QWheelEvent

from msc.es2.types import ES2Field
from msc.es2.unity import Transform


logger = logging.getLogger(__name__)


class MapDockWidget(QDockWidget):
    _file_data: dict[Path, dict[str, ES2Field]]

    def __init__(self, *args, **kwargs):
        super().__init__("Map view", *args, **kwargs)

        self.setVisible(False)
        self.reset()

        self._map_widget = MapWidget()
        self.setWidget(self._map_widget)

    def reset(self):
        self._file_data = {}

    def add_file_data(self, filename: Path, data: dict[str, ES2Field]):
        logger.info("Adding file data '%s'", filename)
        self._file_data[filename] = data

    def remove_file_data(self, filename: Path):
        if filename in self._file_data:
            logger.info("Removing file data '%s'", filename)
            del self._file_data[filename]


def _scale_from_game_coordinates(game_x: float, game_z: float) -> QPointF:
    transform = QTransform()
    transform.scale(0.491, -0.457)
    transform.translate(907.8 / 0.491, 828.6 / -0.457)

    game_coord = QPointF(game_x, game_z)

    return transform.map(game_coord)


_marker_colors = cycle(
    [
        Qt.GlobalColor.magenta,
        Qt.GlobalColor.red,
        Qt.GlobalColor.blue,
        Qt.GlobalColor.green,
        Qt.GlobalColor.yellow,
        Qt.GlobalColor.cyan,
    ]
)


class MapWidget(QWidget):
    _scene: QGraphicsScene
    _view: QGraphicsView
    _background: QPixmap

    markers: dict[str, list]

    class GraphicsView(QGraphicsView):
        factor = 1.5

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
            self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        def wheelEvent(self, event: QWheelEvent | None) -> None:
            if not event:
                return
            if event.angleDelta().y() > 0:
                self.zoom_in()
            elif event.angleDelta().y() < 0:
                self.zoom_out()

        def zoom_in(self):
            self.scale(self.factor, self.factor)

        def zoom_out(self):
            self.scale(1 / self.factor, 1 / self.factor)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.markers = {}

        self._scene = QGraphicsScene(self)

        self._background = QPixmap("gui/perjarvi_road_map.png")
        self._scene_map_widget = self._scene.addPixmap(self._background)

        self._view = MapWidget.GraphicsView(self._scene)
        self._view.fitInView(
            self._scene.itemsBoundingRect(),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

        verticalLayout = QVBoxLayout()
        self.setLayout(verticalLayout)
        layout = verticalLayout
        layout.insertWidget(1, self._view)

    def add_marker(self, tag: str, item: Transform):
        if tag in self.markers:
            return
        position = item.position

        pos = _scale_from_game_coordinates(position.x, position.z)

        if not QRectF(self._background.rect()).contains(pos):
            logger.warning(
                "Not adding marker because out of bounds '%s' @ '%s", tag, pos
            )
            return

        color = next(_marker_colors)
        text = self._scene.addText(tag)
        box = self._scene.addRect(QRectF(0, 0, 5, 5), color, color)
        assert text is not None
        assert box is not None
        text.setDefaultTextColor(color)
        text.setPos(pos)
        box.setPos(pos)

        self.markers[tag] = [text, box]

    def remove_marker(self, tag: str):
        if tag not in self.markers:
            return

        for item in self.markers[tag]:
            self._scene.removeItem(item)

        del self.markers[tag]
