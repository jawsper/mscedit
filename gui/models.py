from enum import Enum
import re
from typing import Any

from PyQt6.QtCore import Qt, QAbstractItemModel, QModelIndex
from ruamel.yaml import YAML

from msc.es2.enums import ES2Key, ES2ValueType
from msc.es2.types import ES2Header, ES2Field


yaml = YAML()


def _truncate_value(value: str, max_length: int = 100):
    if len(value) > max_length:
        return value[:max_length] + "..."
    return value


class TreeItemIndex(int, Enum):
    TAG = 0
    TYPE = 1
    VALUE = 2


class CarPartsEnum(str, Enum):
    TGH = "tightness"
    BLT = "bolts"
    POS = "position"
    WEA = "wear"
    RGB = "color"
    AID = "assembly_id"
    VLV = "valves"
    MT = "material"  # int32; name guessed; on doors, parcel shelf, seats
    DAT = "data"  # various type; name guessed; fueltank (float, level?), rearaxle (str, type?), spring (int), headlight (float)
    DT1 = "data1"
    DT2 = "data2"
    PT = "position/rotation"
    # found on instrumentpanel, seems to be odometer
    D1 = "d1"
    D2 = "d2"
    D3 = "d3"
    # steering rack, left and right adjustment
    TLS = "tls"
    TRS = "trs"
    RAT = "ratio"  # steering rack ratio
    PTT = "ptt"  # something on engine block
    T = "t"  # something on doors, maybe trim?
    CC = "color code"  # found on doors/fenders/bumpers etc


with open("gui/vin.yaml") as f:
    VIN_DATA: dict[str, str] = yaml.load(f)["vin"]


def _header_name(header: ES2Header):
    if header.collection_type != ES2Key.Null:
        if header.key_type != ES2ValueType.Null:
            return f"{header.collection_type.name}[{header.key_type.name}, {header.value_type.name}]"
        return f"{header.collection_type.name}[{header.value_type.name}]"
    return header.value_type.name


def _tag_name(tag: str):
    if tag.lower().startswith("vin"):
        tag_vin = tag[3:6]
        if tag_vin in VIN_DATA:
            friendly_vin = VIN_DATA[tag_vin]
            rest_of_vin = tag[6:]
            match = re.match(
                r"^(?P<variant>[A-Z]?)((?P<index>\d+)(?P<category>[A-Z][A-Z0-9]*))?$",
                rest_of_vin,
            )
            if match:
                friendly_name = f"{tag} - {friendly_vin}"
                if variant := match.group("variant"):
                    friendly_name += f" {variant}"
                if index := match.group("index"):
                    friendly_name += f" [{index}]"
                if category := match.group("category"):
                    if hasattr(CarPartsEnum, category):
                        category = getattr(CarPartsEnum, category).value
                        friendly_name += f" {category}"
                    else:
                        friendly_name += f" {category}"
                return friendly_name
            elif len(rest_of_vin) > 0:
                print(f"FAILED TO MATCH '{tag}' '{friendly_vin}' '{rest_of_vin}'")
            return f"[{friendly_vin}]{rest_of_vin}"
    return tag

class TreeItem(object):
    def __init__(self, data, parent=None):
        self.parentItem = parent
        self.itemData = data
        self.childItems = []

    def appendChild(self, item):
        self.childItems.append(item)

    def child(self, row):
        return self.childItems[row]

    def childCount(self):
        return len(self.childItems)

    def columnCount(self):
        return len(self.itemData)

    def data(self, column):
        try:
            return self.itemData[column]
        except IndexError:
            return None

    def setData(self, column, value):
        if column < 0 or column >= self.columnCount():
            return False
        self.itemData[column] = value
        return True

    def parent(self):
        return self.parentItem

    def row(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)
        return 0


class TreeModel(QAbstractItemModel):
    def __init__(self, data: dict[str, ES2Field] | None, parent=None):
        super(TreeModel, self).__init__(parent)

        self.rootItem = TreeItem(["Tag", "Type", "Value"])
        if data is None:
            return

        self.setupModelData(data, self.rootItem)

    def columnCount(self, parent: QModelIndex) -> int:
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self.rootItem.columnCount()

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        item = index.internalPointer()

        return item.data(index.column())

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.EditRole:
            row = index.row()
            child: TreeItem = self.rootItem.child(row)
            child.setData(index.column(), _truncate_value(str(value)))
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole):
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self.rootItem.data(section)

        return None

    def index(self, row: int, column: int, parent: QModelIndex):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index: Any) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent: QModelIndex) -> int:
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    def setupModelData(self, data: dict[str, ES2Field], parent: TreeItem):
        parents = [parent]
        for tag, entry in data.items():
            header = entry.header
            if header.collection_type != ES2Key.Null:
                if header.key_type != ES2ValueType.Null:
                    header_text = f"{header.collection_type.name}[{header.key_type.name}, {header.value_type.name}]"
                else:
                    header_text = (
                        f"{header.collection_type.name}[{header.value_type.name}]"
                    )
            else:
                header_text = header.value_type.name
            parents[-1].appendChild(
                TreeItem([tag, header_text, _truncate_value(str(entry.value))], parents[-1])
            )

        # indentations = [0]
        # number = 0

        # while number < len(lines):
        #     position = 0
        #     while position < len(lines[number]):
        #         if lines[number][position] != ' ':
        #             break
        #         position += 1

        #     lineData = lines[number][position:].trimmed()

        #     if lineData:
        #         # Read the column data from the rest of the line.
        #         columnData = [s for s in lineData.split('\t') if s]

        #         if position > indentations[-1]:
        #             # The last child of the current parent is now the new
        #             # parent unless the current parent has no children.

        #             if parents[-1].childCount() > 0:
        #                 parents.append(parents[-1].child(parents[-1].childCount() - 1))
        #                 indentations.append(position)

        #         else:
        #             while position < indentations[-1] and len(parents) > 0:
        #                 parents.pop()
        #                 indentations.pop()

        #         # Append a new item to the current parent's list of children.
        #         parents[-1].appendChild(TreeItem(columnData, parents[-1]))

        #     number += 1
