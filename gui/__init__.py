import os
import shutil
from functools import cache
from itertools import cycle
import re

from tabulate import tabulate

from PyQt5.QtCore import Qt, QSortFilterProxyModel, QPoint, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, qApp, QFileDialog, QDialog, QSizePolicy
from PyQt5.QtGui import QPixmap, QPainter, QPen
from PyQt5.uic import loadUi

from msc.es2 import ES2Reader, ES2Writer, ES2ValueType
from gui.models import TreeModel


class EditDialog(QDialog):
    def __init__(self, tag, item, parent=None):
        super().__init__(parent)

        self.tag = tag
        self.item = item

        self.ui = loadUi("gui/EditDialog.ui", self)
        self.ui.widget.set_tag(tag)
        self.ui.widget.set_item(item)

    def get_value(self):
        return self.ui.widget.get_value()


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
        pen = QPen(Qt.red)
        pen.setWidth(10)
        colors = cycle([Qt.magenta, Qt.red, Qt.blue, Qt.green, Qt.yellow, Qt.cyan])
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


class MainWindow(QMainWindow):
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
        self.datamodel.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.datamodel.setSortCaseSensitivity(Qt.CaseInsensitive)
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

    def open_file(self, filename):
        self.filename = filename
        self.open_file_dir = os.path.dirname(self.filename)
        with open(filename, "rb") as f:
            reader = ES2Reader(f)
            self.file_data = reader.read_all()
        self.update_tree(self.file_data)
        self.set_changed(False)
        self.ui.action_Close.setEnabled(True)

    def set_changed(self, changed=True):
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

        with open(self.filename, "wb") as f:
            writer = ES2Writer(f)
            for k, v in self.file_data.items():
                writer.save(k, v)
            writer.save_all()

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
        self.ui.treeView.sortByColumn(0, Qt.AscendingOrder)
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
        index = self.ui.treeView.selectionModel().selection().indexes()[0]
        self.edit_index(index)

    def edit_index(self, index):
        assert self.ui
        assert self.file_data
        tag = index.data()
        dialog = EditDialog(tag, self.file_data[tag], self)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            dialog_result = dialog.get_value()
            if self.file_data[tag].value == dialog_result:
                return
            self.set_changed()
            self.file_data[tag].value = dialog_result
            value_index = self.datamodel.index(index.row(), 2)
            self.datamodel.setData(value_index, dialog_result)

    def searchField_textChanged(self, text):
        self.datamodel.setFilterWildcard(text)

    def show_map(self):
        dialog = MapViewDialog(self.file_data, self)
        dialog.exec_()

    def show_boltchecker(self):
        dialog = BoltCheckerDialog(self.file_data, self)
        dialog.exec_()


class BoltablePart:
    name: str
    bolted: bool

    def __init__(self, *, name: str, bolted, bolts, tightness, installed):
        self.name = name
        self.bolted = bolted  # type: ignore
        self.bolts = bolts
        self.tightness = tightness
        self.installed = installed

    def to_dict(self):
        return {
            k: getattr(self, k)
            for k in ["name", "bolted", "bolts", "tightness", "installed"]
        }


class BoltCheckerDialog(QDialog):
    def __init__(self, model, parent=None):
        super().__init__(parent)

        self.ui = loadUi("gui/BoltCheckerDialog.ui", self)

        self.ui.boltsList.setColumnCount(3)

        self.model = model

        self.find_boltables()

        # from PyQt5.QtWidgets import QTreeWidgetItem

        # self.table = []
        # for part in self.boltable_parts:
        #     self.table.append(part.to_dict())

        # from tabulate import tabulate
        # print(tabulate(sorted(self.table, key=lambda p: p["bolted"]), headers="keys"))
        self.check_bolts()

    def get_part_alternate_names(self, part: str):
        part_names: list[str] = []
        match part:
            # engine bay parts
            case "Valvecover":
                part_names = ["rocker cover"]
            case "ValvecoverGT":
                part_names = ["rocker cover gt"]
            case "Crankwheel":
                part_names = ["crankshaft pulley"]
            case "WiringBatteryPlus":
                part_names = ["battery_terminal_plus"]
            case "WiringBatteryMinus":
                part_names = ["battery_terminal_minus"]

            # interior parts
            case "SteeringWheel":
                part_names = ["stock steering wheel"]
            case "SportWheel":
                part_names = ["sport steering wheel"]
            case "Rally Wheel":
                part_names = ["rally steering wheel"]
            case "SteeringWheelGT":
                part_names = ["gt steering wheel"]
            case "Extinguisher Holder":
                part_names = ["fire extinguisher holder"]

            case _:
                if part.startswith("Gauge"):
                    part_names = [f"{part[5:]} {part[:5]}"]
                elif part.startswith("CrankBearing"):
                    part_names = [f"main bearing{part[-1]}"]
                elif part.startswith("Sparkplug"):
                    part_names = [f"spark plug(clone){part[-1]}"]
                elif part.startswith("Shock_"):
                    position = part.split("_")[1].lower()
                    if position in ["rl", "rr"]:
                        part_names = [f"shock absorber({position}xxx)"]
                    else:
                        part_names = [f"strut {position}(xxxxx)"]
                elif part.startswith("Discbrake"):
                    position = part.split("_")[1].lower()
                    part_names = [f"discbrake({position}xxx)"]
                elif part.startswith("Wishbone"):
                    part_names = [f"IK_{part}"]
                elif part.startswith("Headlight"):
                    position = re.sub(r"^headlight(.+)[12]$", r"\1", part.lower())
                    part_names = [f"headlight {position}"]

        part_names.insert(0, part)
        suffixes = ["(clone)", "(xxxxx)"]
        for suffix in suffixes:
            for part in part_names[:]:
                if suffix in part.lower():
                    continue
                part_names.append(f"{part}{suffix}")
                if "_" in part or " " in part:
                    part_names.append(
                        f"{part.replace('_', '').replace(' ', '')}{suffix}"
                    )

        return part_names

    @cache
    def get_model_keys_with_suffix(self, suffix: str):
        return sorted([key for key in self.model if key.endswith(suffix)])

    def find_model_parts(self, part_names: list[str], suffix: str):
        part_names = [n.lower() for n in part_names]
        keys = self.get_model_keys_with_suffix(suffix)
        for key in keys:
            k = key.removesuffix(suffix).lower()
            if k in part_names:
                return key
            if k.replace("_", "").replace(" ", "") in part_names:
                return key

    def find_part_bolted(self, part_names: list[str]):
        return self.find_model_parts(part_names, "Bolted")

    def find_part_bolts(self, part_names: list[str]):
        return self.find_model_parts(part_names, "Bolts")

    def find_part_tightness(self, part_names: list[str]):
        return self.find_model_parts(part_names, "Tightness")

    def find_part_installed(self, part_names: list[str]):
        return self.find_model_parts(part_names, "Installed")

    def parts_name(self, part):
        if part.startswith("Gauge"):
            part = f"{part[5:]} {part[:5]}"
        return f"{part.lower().replace('_', ' ')}(Clone)"

    def find_boltables(self):
        self.boltable_parts: list[BoltablePart] = []
        not_found = []
        for tag in self.model.keys():
            if tag.endswith("Bolts"):
                part_name = tag[:-5]
                part_names = self.get_part_alternate_names(part_name)
                tag_bolted = self.find_part_bolted(part_names)
                tag_bolts = self.find_part_bolts(part_names)
                tag_tightness = self.find_part_tightness(part_names)
                tag_installed = self.find_part_installed(part_names)
                if tag_bolted and tag_bolts and tag_tightness and tag_installed:
                    part = BoltablePart(
                        name=part_name,
                        bolted=self.model[tag_bolted].value,
                        bolts=self.model[tag_bolts].value,
                        tightness=self.model[tag_tightness].value,
                        installed=self.model[tag_installed].value,
                    )
                    self.boltable_parts.append(part)
                else:
                    not_found.append(
                        {
                            "name": part_name,
                            # "names": part_names,
                            "bolted": tag_bolted,
                            "bolts": tag_bolts,
                            "tightness": tag_tightness,
                            "installed": tag_installed,
                        }
                    )

        self.boltable_parts = sorted(self.boltable_parts, key=lambda part: part.name)

        print(tabulate(not_found, headers="keys"))

    def check_bolts(self):
        pass
