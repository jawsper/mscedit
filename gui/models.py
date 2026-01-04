from PyQt5.QtCore import Qt, QAbstractItemModel, QModelIndex


from msc.es2.enums import ES2Collection, ES2ValueType


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
    def __init__(self, data, parent=None):
        super(TreeModel, self).__init__(parent)

        self.rootItem = TreeItem(["Tag", "Type", "Value"])
        if data is None:
            return

        self.setupModelData(data, self.rootItem)

    def columnCount(self, parent):
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self.rootItem.columnCount()

    def data(self, index, role: Qt.ItemDataRole=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        item = index.internalPointer()

        return item.data(index.column())

    def setData(self, index, value, role: Qt.ItemDataRole=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.EditRole:
            row = index.row()
            child = self.rootItem.child(row)
            child.setData(index.column(), str(value))
            self.dataChanged.emit(index, index)
            return True
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation: Qt.Orientation, role: Qt.ItemDataRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.rootItem.data(section)

        return None

    def index(self, row, column, parent):
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

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent):
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    def setupModelData(self, data, parent):
        parents = [parent]
        for tag, entry in data.items():
            header = entry.header
            if header.collection_type != ES2Collection.Null:
                if header.key_type != ES2ValueType.Null:
                    header_text = f"{header.collection_type.name}[{header.key_type.name}, {header.value_type.name}]"
                else:
                    header_text = (
                        f"{header.collection_type.name}[{header.value_type.name}]"
                    )
            else:
                header_text = header.value_type.name
            parents[-1].appendChild(
                TreeItem([tag, header_text, str(entry.value)], parents[-1])
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
