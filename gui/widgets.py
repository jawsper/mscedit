from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QCheckBox, QLineEdit, QGroupBox, QVBoxLayout, QLabel)
from PyQt5.uic import loadUi

from msc.es2 import ES2Collection, ES2ValueType
from msc.es2.types import ES2Transform, ES2Color, Vector3, Quaternion


class ClickableLabel(QLabel):
    mousePressed = pyqtSignal('QMouseEvent')
    def mousePressEvent(self, event):
        self.mousePressed.emit(event)


class EditWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = loadUi('gui/EditWidget.ui', self)

        self.tag = None
        self.item = None

    def set_tag(self, tag):
        self.tag = tag
        self.ui.label.setText(self.tag)

    def set_item(self, item):
        self.item = item
        self.add_edit_widgets()

    def add_edit_widgets(self):
        if self.item.header.collection_type != ES2Collection.Null:
            if self.item.header.collection_type == ES2Collection.List:
                for item in self.item.value:
                    self._add_edit_widgets_to_layout(
                        self.item.header.value_type,
                        '',
                        item)
        else:
            self._add_edit_widgets_to_layout(
                self.item.header.value_type,
                self.tag,
                self.item.value)
        self.get_widget_container().setAlignment(Qt.AlignTop)

    def _add_edit_widgets_to_layout(self, value_type, label, value):
        wrapper = QWidget()
        wrapper.show()
        wrapper_layout = QVBoxLayout()
        wrapper.setLayout(wrapper_layout)
        for widget in self._make_edit_widgets(
                value_type,
                label,
                value):
            widget.show()
            wrapper_layout.addWidget(widget)
        self.get_widget_container().addWidget(wrapper)

    def _widget_bool(self, label, value):
        widget = QCheckBox()
        widget.setChecked(value)
        widget.setText(label)
        return [widget]

    def __widget_generic_textbox(self, label, value):
        widget = QLineEdit()
        widget.setText(f"{value}")
        return [widget]

    def _widget_float(self, label, value):
        return self.__widget_generic_textbox(label, value)

    def _widget_int(self, label, value):
        return self.__widget_generic_textbox(label, value)

    def _widget_string(self, label, value):
        return self.__widget_generic_textbox(label, value)

    def _widget_transform(self, label, value):
        groupbox = QGroupBox('Position')
        layout = QVBoxLayout()
        groupbox.setLayout(layout)
        for val in value.position.list():
            field = self.__widget_generic_textbox("", val)[0]
            layout.addWidget(field)
        yield groupbox

        groupbox = QGroupBox('Rotation')
        layout = QVBoxLayout()
        groupbox.setLayout(layout)
        for val in value.rotation.list():
            field = self.__widget_generic_textbox("", val)[0]
            layout.addWidget(field)
        yield groupbox

        groupbox = QGroupBox('Scale')
        layout = QVBoxLayout()
        groupbox.setLayout(layout)
        for val in value.scale.list():
            field = self.__widget_generic_textbox("", val)[0]
            layout.addWidget(field)
        yield groupbox

        groupbox = QGroupBox('Layer')
        layout = QVBoxLayout()
        groupbox.setLayout(layout)
        field = self.__widget_generic_textbox("", value.layer)[0]
        layout.addWidget(field)
        yield groupbox

    def _widget_color(self, label, value):
        for component in ('r', 'g', 'b', 'a'):
            val = getattr(value, component)
            widget = self.__widget_generic_textbox("", val)[0]
            yield widget

    def _widget_vector3(self, label, value):
        labels = ('x', 'y', 'z')
        for label, val in zip(labels, value.list()):
            field = QLineEdit()
            field.setText(str(val))
            yield field

    def _make_edit_widgets(self, value_type, label, value):
        widgets = []

        widget_factory = f"_widget_{ES2ValueType(value_type).name}"
        if hasattr(self, widget_factory):
            for widget in getattr(self, widget_factory)(label, value):
                widgets.append(widget)

        return widgets

    def _get_widget_result(self, wrapper, value_type):
        layout = wrapper.layout()
        if layout:
            widget = layout.itemAt(0).widget()
        else:
            widget = wrapper

        if value_type == ES2ValueType.bool:
            return widget.isChecked()

        elif value_type == ES2ValueType.float:
            return float(widget.text())

        elif value_type == ES2ValueType.int:
            return int(widget.text())

        elif value_type == ES2ValueType.string:
            return widget.text()

        elif value_type == ES2ValueType.transform:
            value = ES2Transform()
            # print(layout.count())
            fields = (
                ('position', ES2ValueType.vector3),
                ('rotation', ES2ValueType.quaternion),
                ('scale', ES2ValueType.vector3),
                ('layer', ES2ValueType.string)
            )
            for i, field in enumerate(fields):
                group = layout.itemAt(i).widget()
                field_name, field_type = field
                result = self._get_widget_result(group, field_type)
                setattr(value, field_name, result)
            return value

        elif value_type == ES2ValueType.vector3:
            values = []
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                values.append(self._get_widget_result(widget, ES2ValueType.float))
            return Vector3(*values)

        elif value_type == ES2ValueType.quaternion:
            values = []
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                values.append(self._get_widget_result(widget, ES2ValueType.float))
            return Quaternion(*values)

        elif value_type == ES2ValueType.color:
            values = []
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                values.append(self._get_widget_result(widget, ES2ValueType.float))
            return ES2Color(*values)

    def get_value(self):
        if self.item.header.collection_type != ES2Collection.Null:
            if self.item.header.collection_type == ES2Collection.List:
                value = []
                for i in range(self.get_widget_container().count()):
                    widget = self.get_widget_container().itemAt(i).widget()
                    value.append(self._get_widget_result(widget, self.item.header.value_type))
                return value
        else:
            widget = self.get_widget_container().itemAt(0).widget()
            return self._get_widget_result(widget, self.item.header.value_type)

    def get_widget_container(self):
        return self.ui.editWidgetsContainer.layout()
