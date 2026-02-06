from collections import defaultdict
from enum import Enum
import re
from typing import Any, Self, cast

from PyQt6.QtCore import Qt, QAbstractItemModel, QModelIndex

from msc.es2.types import ES2Field
from .utils import header_name, tag_name


def _truncate_value(value: str, max_length: int = 100):
    if len(value) > max_length:
        return value[:max_length] + "..."
    return value


class TreeItemIndex(int, Enum):
    TAG = 0
    TYPE = 1
    VALUE = 2


class TableItem:
    parent_item: Self | None
    child_items: list[Self]
    checked: Qt.CheckState
    tag: str
    type: str
    value: str

    def __init__(
        self,
        tag: str,
        type: str,
        value: str,
        display_tag: str | None = None,
        parent: Self | None = None,
        checked: Qt.CheckState = Qt.CheckState.Unchecked,
    ):
        self.tag = tag
        self.display_tag = display_tag if display_tag else tag
        self.type = type
        self.value = value

        self.parent_item = parent
        self.child_items = []
        self.checked = checked

    def appendChild(self, item: Self):
        self.child_items.append(item)

    def child(self, row: int):
        return self.child_items[row]

    def childCount(self):
        return len(self.child_items)

    def columnCount(self):
        return 3

    def data(self, column: int, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole):
        match column:
            case 0:
                return self.display_tag
            case 1:
                return self.type
            case 2:
                match role:
                    case Qt.ItemDataRole.DisplayRole:
                        return _truncate_value(self.value)
                    case Qt.ItemDataRole.EditRole:
                        return self.value
                return None
        return None

    def setData(self, column: int, value: Any):
        match column:
            case 0:
                self.display_tag = value
            case 1:
                self.type = value
            case 2:
                self.value = value
            case _:
                return False
        return True

    def parent(self) -> Self:
        return self.parent_item

    def row(self):
        if self.parent_item:
            return cast(Self, self.parent_item).child_items.index(self)
        return 0


class TreeModel(QAbstractItemModel):
    rootItem: TableItem

    def __init__(self, data: dict[str, ES2Field] | None, parent=None):
        super(TreeModel, self).__init__(parent)

        self.rootItem = TableItem("Tag", "Type", "Value")
        if data is None:
            return

        self.setupModelData(data)

    def columnCount(self, parent: QModelIndex) -> int:
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self.rootItem.columnCount()

    def data(
        self, index: QModelIndex, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if not index.isValid():
            return None

        item = cast(TableItem, index.internalPointer())

        match role:
            case Qt.ItemDataRole.UserRole:
                if index.column() == TreeItemIndex.TAG.value:
                    return item.tag
                return None
            case Qt.ItemDataRole.CheckStateRole:
                if index.column() == TreeItemIndex.TAG.value:
                    return item.checked
            case Qt.ItemDataRole.DisplayRole | Qt.ItemDataRole.EditRole:
                return item.data(index.column(), role)
        return None

    def setData(
        self,
        index: QModelIndex,
        value: Any,
        role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole,
    ):
        item = cast(TableItem, index.internalPointer())
        match role:
            case Qt.ItemDataRole.EditRole:
                item.setData(index.column(), str(value))
                self.dataChanged.emit(index, index)
                return True
            case Qt.ItemDataRole.CheckStateRole:
                item.checked = value
                self.dataChanged.emit(index, index, [role])
                return True

        return False

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsUserCheckable
        )

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole
    ):
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

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()

        childItem = cast(TableItem, index.internalPointer())
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        try:
            return self.createIndex(parentItem.row(), 0, parentItem)
        except:
            raise

    def rowCount(self, parent: QModelIndex) -> int:
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = cast(TableItem, parent.internalPointer())

        return parentItem.childCount()

    def setupModelData(self, data: dict[str, ES2Field]):
        # regex = re.compile(r"^(?P<key>\D.+?)(\d+)$")
        # data_items = sorted(
        #     [
        #         (m.group("key"), tag)
        #         for tag, item in data.items()
        #         if item.header.value_type == ES2ValueType.int32
        #         and not tag.startswith("VIN")
        #         and (m := regex.match(tag))
        #     ],
        #     key=lambda r: r[0],
        # )
        # from rich import print as rprint

        # rprint(data_items)

        grouped_items_prefixes = [
            r"^(?P<prefix>VIN(\d{3})[B-Z]?)",
            # r"^(?P<prefix>[A-Za-z][A-Za-z]+0?)",
        ]

        grouped_items: defaultdict[str, list] = defaultdict(list)
        shopping_bags: defaultdict[str, dict] = defaultdict(dict)

        for tag, entry in data.items():
            # if tag.startswith("shoppingbag"):
            #     m = re.match(r"^(?P<id>shoppingbag\d+)(?P<name>\w*)$", tag)
            #     if m:
            #         id = m.group("id")
            #         if id in data:  # no root entry means bag is gone
            #             shopping_bags[id][m.group("name")] = entry.value
            #             continue

            for prefix in grouped_items_prefixes:
                if m := re.match(prefix, tag):
                    grouped_items[m.group("prefix")].append((tag, entry))
                    break
            else:
                display_tag = tag_name(tag)
                item = TableItem(
                    tag,
                    header_name(entry.header),
                    str(entry.value),
                    display_tag,
                    self.rootItem,
                )
                self.rootItem.appendChild(item)

        for prefix, items in grouped_items.items():
            entry = data[prefix] if prefix in data else None
            root_item = TableItem(
                prefix,
                header_name(entry.header) if entry else "",
                str(entry.value) if entry else "",
                tag_name(prefix),
                self.rootItem,
            )
            self.rootItem.appendChild(root_item)
            for tag, entry in items:
                if tag == prefix:
                    continue
                display_tag = tag_name(tag)
                tree_item = TableItem(
                    tag,
                    header_name(entry.header),
                    str(entry.value),
                    display_tag,
                    root_item,
                )
                root_item.appendChild(tree_item)

        for shopping_bag_id, shopping_bag in shopping_bags.items():
            shopping_bag_root = data[shopping_bag_id]
            item = TableItem(
                shopping_bag_id,
                header_name(shopping_bag_root.header),
                str(shopping_bag_root.value),
                shopping_bag_id,
                self.rootItem,
            )
            self.rootItem.appendChild(item)

            for key, value in shopping_bag.items():
                if key in ("", "Keys", "Values"):
                    continue
                tag = f"{shopping_bag_id}{key}"
                entry = data[tag]
                sub_item = TableItem(
                    tag, header_name(entry.header), str(entry.value), key, item
                )
                item.appendChild(sub_item)

            contents_item = TableItem("", "", "", "Contents", item)
            item.appendChild(contents_item)

            contents: dict[str, str] = dict(
                zip(shopping_bag["Keys"], shopping_bag["Values"])
            )
            for name, count in contents.items():
                # f"{shopping_bag_id}{name}",
                sub_item = TableItem("", "", count, name, contents_item)
                contents_item.appendChild(sub_item)
