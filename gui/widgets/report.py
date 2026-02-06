import logging
from pathlib import Path
import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDockWidget,
    QWidget,
    QTableView,
    QVBoxLayout,
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem

from msc.es2.enums import ES2ValueType, ES2Key
from msc.es2.types import ES2Field
from ..utils import PARTS_DATA, tag_name2, parse_tag, scale_value

logger = logging.getLogger(__name__)


class ReportDockWidget(QDockWidget):
    _file_data: dict[Path, dict[str, ES2Field]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle("Car report")

        self.report = ReportWidget()
        self.setWidget(self.report)
        # self.setMinimumSize(self.report.table_widget.size())

    def reset(self):
        self._file_data = {}

    def add_file_data(self, filename: Path, data: dict[str, ES2Field]):
        if "VIN1010AID" not in data:
            logger.debug("Not adding data, missing VIN1010AID '%s'", filename)
            return
        logger.info("Adding file data '%s'", filename)

        self._file_data[filename] = data

        self.report.set_data(data)

    def remove_file_data(self, filename: Path):
        if filename in self._file_data:
            logger.info("Removing file data '%s'", filename)
            del self._file_data[filename]


class ReportWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.table_widget = QTableView()
        self.table_widget.setSortingEnabled(True)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Part", "Condition"])
        self.table_widget.setModel(self.model)
        layout.addWidget(self.table_widget)

    def set_data(self, data: dict[str, ES2Field]):
        sorted_data: dict[str, ES2Field] = {k: data[k] for k in sorted(data.keys())}

        aid_names: list[str] = [
            tag for tag in sorted_data.keys() if tag.endswith("AID")
        ]

        installed_aids = {
            tag: item
            for tag, item in sorted_data.items()
            if tag.endswith("AID")
            and item.header.collection_type == ES2Key.Null
            and item.header.value_type == ES2ValueType.int32
            and item.value > 0
        }

        installed_parts: dict[str, dict] = {}
        for tag in sorted(aid_names):
            part_prefix = tag.removesuffix("AID")
            all_values_for_part: list[str] = [
                tag.removeprefix(part_prefix)
                for tag in data.keys()
                if tag.startswith(part_prefix)
                and not re.match(r"^\d", tag.removeprefix(part_prefix))
            ]
            if tag not in installed_aids:
                continue
            part_tags: list[str] = [
                f"{part_prefix}{value}" for value in all_values_for_part
            ]

            installed_parts[part_prefix] = {
                tag.removeprefix(part_prefix): data[tag].value for tag in part_tags
            }
            installed_parts[part_prefix]["name"] = parse_tag(part_prefix)

        parts_list = []

        skip_wear = set()

        for part_name, part_data in PARTS_DATA.items():
            found_parts = [
                tag
                for tag in installed_parts.keys()
                if tag.lower().startswith(part_name.lower())
            ]
            if not found_parts:
                continue
            for row in found_parts:
                installed_part = installed_parts[row]
                for val_name, val_data in part_data.items():
                    if not val_data:
                        continue
                    if val_name in installed_part:
                        score = None
                        if "range" in val_data:
                            score = scale_value(
                                installed_part[val_name],
                                val_data["range"]["min"],
                                val_data["range"]["max"],
                                0,
                                100,
                            )
                        parts_list.append(
                            {
                                "name": tag_name2(installed_part["name"]),
                                "key": val_data["name"],
                                "value": installed_part[val_name],
                                "score": score,
                            }
                        )
                        if val_name == "WEA":
                            skip_wear.add(part_prefix)
                        # print(val_name, installed_part[val_name], val_data)

        for part_prefix, installed_part in installed_parts.items():
            if part_prefix in skip_wear:
                continue
            if "WEA" in installed_part:
                parts_list.append(
                    {
                        "name": tag_name2(installed_part["name"]),
                        "key": "wear",
                        "value": installed_part["WEA"],
                        "score": installed_part["WEA"],
                    }
                )

        for row_data in parts_list:
            items = []
            for col in ["name", "key", "value"]:
                col_data = row_data[col]
                item = QStandardItem(str(col_data))
                if (
                    col == "value"
                    and "score" in row_data
                    and row_data["score"] is not None
                ):
                    score = row_data["score"]
                    color = Qt.GlobalColor.yellow
                    if score > 75:
                        color = Qt.GlobalColor.green
                    elif score < 25:
                        color = Qt.GlobalColor.red
                    item.setBackground(color)
                items.append(item)
            self.model.appendRow(items)

        # print(parts_list)
