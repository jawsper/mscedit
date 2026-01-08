from dataclasses import dataclass, field
from typing import Any

from msc.es2.enums import ES2Key, ES2ValueType


@dataclass
class ES2HeaderSettings:
    encrypt: bool = False
    debug: bool = False


@dataclass
class ES2Header:
    collection_type: ES2Key = ES2Key.Null
    key_type: ES2ValueType = ES2ValueType.Null
    value_type: ES2ValueType = ES2ValueType.Null
    settings: ES2HeaderSettings = field(default_factory=ES2HeaderSettings)


@dataclass
class ES2Tag:
    tag: str = ""
    position: int = 0
    settings_position: int = 0
    next_tag_position: int = 0



@dataclass
class ES2Field:
    header: ES2Header
    value: Any

    @classmethod
    def from_value_type(cls, value_type: ES2ValueType, value: Any):
        return cls(ES2Header(value_type=value_type), value)
