import logging
from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QFrame,
    QLabel,
    QLayout,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
)

from msc.es2.enums import ES2Key, ES2ValueType
from msc.es2.types import (
    ES2Field,
)
from msc.es2.unity import (
    Color,
    Quaternion,
    Texture2D,
    Transform,
    Vector3,
)

logger = logging.getLogger(__name__)


class EditWidget(QWidget):
    tag: str
    item: ES2Field

    _layout: QVBoxLayout
    _label: QLabel
    _scroll_area: QScrollArea
    _form_widget: QWidget
    _form_layout: QFormLayout

    def __init__(self, parent: QWidget | None = None, *, tag: str, item: ES2Field):
        super().__init__(parent)

        self._layout = QVBoxLayout(self)
        self._label = QLabel()
        self._label.setText(tag)
        self._layout.addWidget(self._label)
        self._scroll_area = QScrollArea()
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.setWidgetResizable(True)
        self._form_widget = QWidget()
        self._form_widget.setGeometry(0, 0, 382, 256)
        self._form_layout = QFormLayout(self._form_widget)
        self._layout.addWidget(self._scroll_area)
        self._scroll_area.setWidget(self._form_widget)

        self.tag = tag
        self.item = item

        match self.item.header.collection_type:
            case ES2Key.NativeArray | ES2Key.List:
                for item in self.item.value:
                    self._add_edit_widgets_to_layout(
                        self.item.header.value_type, "", item
                    )
            case ES2Key.Dictionary:
                for key, value in self.item.value.items():
                    self._add_edit_widgets_to_layout(
                        self.item.header.value_type, key, value, is_dict=True
                    )
            case ES2Key.Null:
                self._add_edit_widgets_to_layout(
                    self.item.header.value_type, self.tag, self.item.value
                )
            case _:
                logger.warning(
                    f"Cannot render widgets for {self.item.header.collection_type}"
                )

    def _add_edit_widgets_to_layout(
        self, value_type: ES2ValueType, label, value, *, is_dict: bool = False
    ):
        layout = self._form_layout
        for widget in self._make_edit_widgets(value_type, label, value):
            if is_dict:
                layout.addRow(label, widget)
            else:
                layout.addRow(widget)

    def _widget_bool(self, label, value: bool):
        widget = QCheckBox()
        widget.setChecked(value)
        widget.setText(label)
        return [widget]

    def _widget_byte(self, label, value: int):
        return self.__widget_generic_textbox(label, value)

    def __widget_generic_textbox(self, label, value):
        widget = QLineEdit()
        widget.setText(f"{value}")
        return [widget]

    def _widget_float(self, label, value: float):
        return self.__widget_generic_textbox(label, value)

    def _widget_int32(self, label, value: int):
        return self.__widget_generic_textbox(label, value)

    def _widget_string(self, label, value: str):
        return self.__widget_generic_textbox(label, value)

    def _widget_transform(self, label, value: Transform):
        groupbox = QGroupBox("Position")
        layout = QVBoxLayout()
        groupbox.setLayout(layout)
        for val in value.position.as_list():
            field = self.__widget_generic_textbox("", val)[0]
            layout.addWidget(field)
        yield groupbox

        groupbox = QGroupBox("Rotation")
        layout = QVBoxLayout()
        groupbox.setLayout(layout)
        for val in value.rotation.as_list():
            field = self.__widget_generic_textbox("", val)[0]
            layout.addWidget(field)
        yield groupbox

        groupbox = QGroupBox("Scale")
        layout = QVBoxLayout()
        groupbox.setLayout(layout)
        for val in value.scale.as_list():
            field = self.__widget_generic_textbox("", val)[0]
            layout.addWidget(field)
        yield groupbox

        groupbox = QGroupBox("Layer")
        layout = QVBoxLayout()
        groupbox.setLayout(layout)
        field = self.__widget_generic_textbox("", value.layer)[0]
        layout.addWidget(field)
        yield groupbox

    def _widget_color(self, label, value: Color):
        labels = ("r", "g", "b", "a")
        for label, val in zip(labels, value.as_list()):
            widget = self.__widget_generic_textbox("", val)[0]
            yield widget
        color = QLabel(text="Color!")
        color.setStyleSheet(
            "border: 1px solid black; "
            f"background-color: {value.to_css()};"
        )
        yield color

    def _widget_vector3(self, label, value: Vector3):
        labels = ("x", "y", "z")
        for label, val in zip(labels, value.as_list()):
            field = QLineEdit()
            field.setText(str(val))
            yield field

    def _widget_texture2d(self, label, value: Texture2D):
        image = QLabel()
        pixmap = QPixmap()
        pixmap.loadFromData(value.image)
        image.setPixmap(pixmap)
        image.setScaledContents(True)
        yield image

    def _make_edit_widgets(self, value_type: ES2ValueType, label, value):
        widgets = []

        widget_factory = f"_widget_{value_type.name}"
        if hasattr(self, widget_factory):
            for widget in getattr(self, widget_factory)(label, value):
                widgets.append(widget)
        else:
            logger.warning("No widget factory for type '%s'", value_type.name)

        return widgets

    def _get_widget_result(
        self,
        wrapper: QLayout | QWidget,
        value_type: ES2ValueType,
    ):
        layout = wrapper.layout()
        if layout:
            widget: QWidget = layout.itemAt(0).widget()
        else:
            widget: QWidget = wrapper

        match value_type:
            case ES2ValueType.bool:
                return cast(QCheckBox, widget).isChecked()

            case ES2ValueType.float:
                return float(cast(QLineEdit, widget).text())

            case ES2ValueType.int32 | ES2ValueType.byte:
                return int(cast(QLineEdit, widget).text())

            case ES2ValueType.string:
                return cast(QLineEdit, widget).text()

            case ES2ValueType.transform:
                value = Transform()
                fields = (
                    ("position", ES2ValueType.vector3),
                    ("rotation", ES2ValueType.quaternion),
                    ("scale", ES2ValueType.vector3),
                    ("layer", ES2ValueType.string),
                )
                for i, (field_name, field_type) in enumerate(fields):
                    group = layout.itemAt(i).widget()
                    result = self._get_widget_result(group, field_type)
                    setattr(value, field_name, result)
                return value

            case ES2ValueType.vector3:
                values = []
                for i in range(layout.count()):
                    widget = layout.itemAt(i).widget()
                    values.append(self._get_widget_result(widget, ES2ValueType.float))
                return Vector3(*values)

            case ES2ValueType.quaternion:
                values = []
                for i in range(layout.count()):
                    widget = layout.itemAt(i).widget()
                    values.append(self._get_widget_result(widget, ES2ValueType.float))
                return Quaternion(*values)

            case ES2ValueType.color:
                values = []
                for i in range(layout.count()):
                    widget = layout.itemAt(i).widget()
                    if isinstance(widget, QLineEdit):
                        values.append(
                            self._get_widget_result(widget, ES2ValueType.float)
                        )
                return Color(*values)

    def get_value(self):
        form_layout = self._form_layout
        assert self.item
        match self.item.header.collection_type:
            case ES2Key.NativeArray | ES2Key.List:
                value = []
                for i in range(form_layout.rowCount()):
                    widget = cast(
                        QWidget,
                        form_layout.itemAt(i, QFormLayout.ItemRole.FieldRole).widget(),
                    )
                    value.append(
                        self._get_widget_result(widget, self.item.header.value_type)
                    )
                return value
            case ES2Key.Dictionary:
                value = {}
                for i in range(form_layout.rowCount()):
                    label = cast(
                        QLabel,
                        form_layout.itemAt(i, QFormLayout.ItemRole.LabelRole).widget(),
                    )
                    value_widget = cast(
                        QWidget,
                        form_layout.itemAt(i, QFormLayout.ItemRole.FieldRole).widget(),
                    )
                    k = label.text()
                    v = self._get_widget_result(
                        value_widget,
                        self.item.header.value_type,
                    )
                    value[k] = v
                return value
            case ES2Key.Null:
                return self._get_widget_result(
                    form_layout,
                    self.item.header.value_type,
                )
            case _:
                logger.warning(
                    f"Cannot get value for {self.item.header.collection_type}"
                )
        logger.warning("No value was returned.")

    def get_widget_container(self) -> QFormLayout:
        return self._form_layout
