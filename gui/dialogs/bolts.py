from functools import cache
import re

# from tabulate import tabulate

from PyQt6.QtWidgets import QDialog
from PyQt6.uic.load_ui import loadUi


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

        # from PyQt6.QtWidgets import QTreeWidgetItem

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

        # print(tabulate(not_found, headers="keys"))

    def check_bolts(self):
        pass
