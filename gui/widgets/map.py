from itertools import cycle
import logging
from pathlib import Path

from PyQt6.QtCore import pyqtSlot, Qt, QPointF, QRectF
from PyQt6.QtWidgets import (
    QDockWidget,
    QGraphicsScene,
    QGraphicsView,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QPixmap, QTransform

from msc.es2.types import ES2Field
from msc.es2.unity import Transform


logger = logging.getLogger(__name__)


class MapDockWidget(QDockWidget):
    _file_data: dict[Path, dict[str, ES2Field]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle("Map view")

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


def _scale_from_game_coordinates(
    game_x: float,
    game_z: float,
    width: float,
    height: float,
) -> QPointF | None:
    """
    Scales game_x to background image size using GAME_X_RANGE
    Scales game_z to background image height using GAME_Y_RANGE
    """
    GAME_X_RANGE = -1851, 2334
    GAME_Z_RANGE = 1823, -1548

    if not (GAME_X_RANGE[0] <= game_x <= GAME_X_RANGE[1]) or (
        not (GAME_Z_RANGE[1] <= game_z <= GAME_Z_RANGE[0])
    ):
        return None

    def scale_value(
        old_value: float,
        old_min: float,
        old_max: float,
        new_min: float,
        new_max: float,
    ) -> float:
        return (
            (new_max - new_min) * (old_value - old_min) / (old_max - old_min)
        ) + new_min

    display_x = scale_value(
        game_x,
        GAME_X_RANGE[0],
        GAME_X_RANGE[1],
        0,
        width,
    )
    display_y = scale_value(
        game_z,
        GAME_Z_RANGE[0],
        GAME_Z_RANGE[1],
        0,
        height,
    )

    return QPointF(display_x, display_y)


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
    factor = 1.5
    _scene: QGraphicsScene
    _view: QGraphicsView

    markers: dict[str, list]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.markers = {}

        self._scene = QGraphicsScene(self)

        self._background = QPixmap("gui/perjarvi_road_map.png")
        self._scene_map_widget = self._scene.addPixmap(self._background)

        self._view = QGraphicsView(self._scene)
        self._view.fitInView(
            self._scene.itemsBoundingRect(),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

        verticalLayout = QVBoxLayout()
        self.setLayout(verticalLayout)
        layout = verticalLayout
        layout.insertWidget(1, self._view)

        # QShortcut(
        #     QKeySequence(QKeySequence.StandardKey.ZoomIn),
        #     self._view,
        #     context=Qt.ShortcutContext.WidgetShortcut,
        #     # activated=self.zoom_in,
        # ).activated.connect(self.zoom_in)

        # QShortcut(
        #     QKeySequence(QKeySequence.StandardKey.ZoomOut),
        #     self._view,
        #     context=Qt.ShortcutContext.WidgetShortcut,
        #     # activated=self.zoom_out,
        # ).activated.connect(self.zoom_out)

    @pyqtSlot()
    def zoom_in(self):
        scale_tr = QTransform()
        scale_tr.scale(self.factor, self.factor)

        tr = self._view.transform() * scale_tr
        self._view.setTransform(tr)

    @pyqtSlot()
    def zoom_out(self):
        scale_tr = QTransform()
        scale_tr.scale(self.factor, self.factor)

        scale_inverted, invertible = scale_tr.inverted()

        if invertible:
            tr = self._view.transform() * scale_inverted
            self._view.setTransform(tr)

    def add_marker(self, tag: str, item: Transform):
        if tag in self.markers:
            return
        position = item.position

        pos = _scale_from_game_coordinates(
            position.x, position.z, self._background.width(), self._background.height()
        )

        if pos is None:
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
