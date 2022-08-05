import os
import shutil
from itertools import cycle
import re

from PyQt5.QtCore import (Qt, QSortFilterProxyModel, QPoint, pyqtSignal)
from PyQt5.QtWidgets import (QMainWindow, qApp, QFileDialog, QDialog, QSizePolicy)
from PyQt5.QtGui import (QPixmap, QPainter, QPen)
from PyQt5.uic import loadUi

from msc.es2 import ES2Reader, ES2Writer, ES2ValueType
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


class MapViewDialog(QDialog):
    def __init__(self, model, parent=None):
        super().__init__(parent)

        self.model = model

        self.ui = loadUi('gui/MapViewDialog.ui', self)
        self.ui.addItemButton.clicked.connect(self.button_add_clicked)
        self.ui.clearButton.clicked.connect(self.button_clear_clicked)

        transform_tags = []
        for tag, item in self.model.items():
            if item.header.value_type == ES2ValueType.transform:
                transform_tags.append(tag)

        for tag in sorted(transform_tags):
            self.ui.selectionBox.addItem(tag)

        self.background = QPixmap('gui/perjarvi_road_map.png')
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
        print('map_mouse_pressed')
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
            return ( (new_max - new_min) * (old_value - old_min) / (old_max - old_min) ) + new_min
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

        self.open_file_dir = os.path.expanduser('~')

        self.ui = loadUi('gui/MainWindow.ui', self)

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
        self.set_changed(False)
        self.ui.action_Close.setEnabled(True)

    def set_changed(self, changed=True):
        self.data_changed = changed
        self.ui.action_Save.setEnabled(self.data_changed)

    def menu_save(self):
        for i in range(100):
            backup_filename = '{}.{}'.format(self.filename, i) 
            if not os.path.exists(backup_filename):
                shutil.copy2(self.filename, backup_filename)
                break
        else:
            raise Exception('Too many backups!')

        with open(self.filename, 'wb') as f:
            writer = ES2Writer(f)
            for k, v in self.file_data.items():
                writer.save(k, v)
            writer.save_all()

        self.set_changed(False)

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
        pass
        # indexes = self.ui.treeView.selectionModel().selection().indexes()
        # if len(indexes) > 0:
        #     index = indexes[0]
        #     tag = self.datamodel.data(index)
        #     print('selectionChanged')
        #     print(self.file_data[item].header.value_type)
        #     print(self.file_data[item].value)

    def treeView_doubleClicked(self):
        index = self.ui.treeView.selectionModel().selection().indexes()[0]
        self.edit_index(index)

    def edit_index(self, index):
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
    def __init__(self, name, model, **tags):
        self.name = name
        for value_name, tag_name in tags.items():
            value = model[tag_name].value
            setattr(self, value_name, value)


class BoltCheckerDialog(QDialog):
    def __init__(self, model, parent=None):
        super().__init__(parent)

        self.ui = loadUi('gui/BoltCheckerDialog.ui', self)

        self.ui.boltsList.setColumnCount(3)

        self.model = model

        self.find_boltables()

        # from PyQt5.QtWidgets import QTreeWidgetItem
        
        self.table = []
        for part in self.boltable_parts:
            pass
            # print(part.name, part.bolted)

        # from tabulate import tabulate
        # print(tabulate(sorted(self.table, key=lambda x: x[1])))
        self.check_bolts()

    def get_tag_bolted(self, part):
        tag_name = None
        if part.startswith('Gauge'):
            part = part[5:] + ' ' + part[:5]
        elif part == 'SteeringWheel':
            part = 'stock steering wheel'
        elif part == 'SportWheel':
            part = 'sport steering wheel'
        elif part == 'Rally Wheel':
            part = 'rally steering wheel'
        elif part.startswith('CrankBearing'):
            part = 'main bearing' + part[-1]
        elif part.startswith('Sparkplug'):
            part = 'spark plug(clone)' + part[-1]
        elif part == 'Valvecover':
            part = 'rocker cover'
        elif part == 'Crankwheel':
            part = 'crankshaft pulley'
        elif part.startswith('Shock_'):
            position = re.sub(r'^.+_(.+)$', r'\1', part).lower()
            if position in ['rl', 'rr']:
                part = 'shock absorber({}xxx)'.format(position)
            else:
                part = 'strut {}(xxxxx)'.format(position)
        elif part.startswith('Discbrake'):
            position = re.sub(r'^.+_(.+)$', r'\1', part).lower()
            part = 'discbrake({}xxx)'.format(position)
        elif part.startswith('Wishbone'):
            part = 'IK_' + part
        elif part.startswith('Headlight'):
            position = re.sub(r'^Headlight(.+)$', r'\1', part).lower()
            part = 'headlight(' + position + ((5 - len(position)) * 'x') + ')'

        for tag in self.model:
            if not tag.endswith('Bolted'):
                continue
            tag_name = tag[:-6]  # strip "Bolted"
            tag_name = tag_name.replace(' ', '').replace('_', '').lower()
            part_name = part.replace(' ', '').replace('_', '').lower()
            # tag_name = re.sub(r'\(.+\)', '', tag_name)  # strip "(Clone)"
            if tag_name == part_name:
                return tag
            if tag_name.replace('(clone)','') == part_name:
                return tag
            if tag_name.replace('(xxxxx)', '') == part_name:
                return tag
            # if tag.replace('_', '').replace(' ', '').lower().startswith(part.replace('_', '').replace(' ','').lower()):
            #     self.table.append([tag_name, part_name])
            #     return tag

    def get_tag_bolts(self, part):
        return part + 'Bolts'

    def get_tag_tightness(self, part):
        return part + 'Tightness'

    def parts_name(self, part):
        if part.startswith('Gauge'):
            part = part[5:] + ' ' + part[:5]
        return part.lower().replace('_', ' ') + '(Clone)'

    def bolts_name(self, part):
        return part

    def find_boltables(self):
        self.boltable_parts = []
        for tag in self.model.keys():
            if tag.endswith('Bolts'):
                part_name = tag[:-5]
                tag_bolted = self.get_tag_bolted(part_name)
                tag_bolts = self.get_tag_bolts(part_name)
                tag_tightness = self.get_tag_tightness(part_name)
                if tag_bolted in self.model and tag_bolts in self.model and tag_tightness in self.model:
                    part = BoltablePart(part_name, self.model,
                        bolted=tag_bolted,
                        bolts=tag_bolts,
                        tightness=tag_tightness)
                    self.boltable_parts.append(part)
                else:
                    print(part_name)

    def check_bolts(self):
        pass