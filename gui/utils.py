from enum import Enum
import logging
import re

from ruamel.yaml import YAML

from msc.es2.enums import ES2Key, ES2ValueType
from msc.es2.types import ES2Header

logger = logging.getLogger(__name__)
yaml = YAML()

with open("gui/vin.yaml") as f:
    __raw_yaml = yaml.load(f)
    PARTS_DATA: dict[str, dict] = __raw_yaml["parts"]
    VIN_DATA: dict[str, str] = __raw_yaml["vin"]


def header_name(header: ES2Header):
    if header.collection_type != ES2Key.Null:
        if header.key_type != ES2ValueType.Null:
            return f"{header.collection_type.name}[{header.key_type.name}, {header.value_type.name}]"
        return f"{header.collection_type.name}[{header.value_type.name}]"
    return header.value_type.name


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
    # also about instrumentpanel; A: no clock, B: clock, C: tacho
    D1 = "d1" # odo precision
    D2 = "d2" # odo shown
    D3 = "d3" # features
    """
    0: radio + switch
    1: radio + no switch
    2: no radio, switch
    3: no radio, no switch <- to be confirmed but pretty certain
    """
    # steering rack, left and right adjustment
    TLS = "tls"
    TRS = "trs"
    RAT = "ratio"  # steering rack ratio
    PTT = "ptt"  # something on engine block
    T = "t"  # something on doors, maybe trim?
    CC = "color code"  # found on doors/fenders/bumpers etc


def parse_tag(tag: str):
    parsed_tag: dict[str, str] = {"name": tag}
    if tag.lower().startswith("vin"):
        tag_vin = tag[3:6]
        if tag_vin in VIN_DATA:
            parsed_tag["name"] = f"VIN{tag_vin}"
            friendly_vin = VIN_DATA[tag_vin]
            rest_of_vin = tag[6:]
            match = re.match(
                r"^(?P<variant>[A-Z]?)((?P<index>\d+)(?P<category>[A-Z][A-Z0-9]*)?)?$",
                rest_of_vin,
            )
            parsed_tag["friendly_vin"] = friendly_vin
            if match:
                if variant := match.group("variant"):
                    parsed_tag["variant"] = variant
                if index := match.group("index"):
                    parsed_tag["index"] = index
                if category := match.group("category"):
                    if hasattr(CarPartsEnum, category):
                        category = getattr(CarPartsEnum, category).value
                    parsed_tag["category"] = category
            elif len(rest_of_vin) > 0:
                logger.warning(
                    f"FAILED TO MATCH '{tag}' '{friendly_vin}' '{rest_of_vin}'"
                )
                parsed_tag["rest_of_vin"] = rest_of_vin
    return parsed_tag


def tag_name2(parsed_tag: dict):
    if "friendly_vin" in parsed_tag:
        return parsed_tag["friendly_vin"]
    return parsed_tag["name"]


def tag_name(tag: str):
    if tag.lower().startswith("vin"):
        tag_vin = tag[3:6]
        if tag_vin in VIN_DATA:
            friendly_vin = VIN_DATA[tag_vin]
            rest_of_vin = tag[6:]
            match = re.match(
                r"^(?P<variant>[A-Z]?)((?P<index>\d+)(?P<category>[A-Z][A-Z0-9]*)?)?$",
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
                logger.warning(
                    f"FAILED TO MATCH '{tag}' '{friendly_vin}' '{rest_of_vin}'"
                )
            return f"[{friendly_vin}]{rest_of_vin}"
    return tag


def scale_value(
    old_value: float, old_min: float, old_max: float, new_min: float, new_max: float
) -> float:
    return ((new_max - new_min) * (old_value - old_min) / (old_max - old_min)) + new_min
