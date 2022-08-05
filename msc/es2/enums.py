from enum import Enum, IntEnum


class ES2Collection(Enum):
    NativeArray = 81
    Dictionary = 82
    List = 83
    HashSet = 84
    Queue = 85
    Stack = 86
    Size = 122
    Terminator = 123
    Null = 124
    Settings = 125
    Tag = 126
    Encrypt = 127


class ES2ValueType(IntEnum):
    Null = 0
    transform = 159054454
    color = 852446001
    float = 1849612139
    bool = 2907536540
    int = 3802662998
    string = 4259967470
    mesh = 2420697311
    quaternion = 121  # TODO: find actual hash!
    vector2 = 122  # TODO: find actual hash!
    vector3 = 0xEC66DC46
    vector4 = 124  # TODO: find actual hash!
    matrix4x4 = 125  # TODO: find actual hash!
    boneweight = 126  # TODO: find actual hash!
