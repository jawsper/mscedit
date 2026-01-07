from enum import Enum, IntEnum


class ES2Key(Enum):
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


class ES2ValueTypeMap(str, Enum):
    """
    This enum is used to map the function names with the C# types.
    This is used to get the integer hash needed by ES2ValueType,
    by putting the value msc.type_get_hash, which gives the integer hash.
    """
    byte = "System.Byte"
    bool = "System.Boolean"
    string = "System.String"
    int32 = "System.Int32"
    float = "System.Single"
    boneweight = "UnityEngine.BoneWeight"
    color = "UnityEngine.Color"
    matrix4x4 = "UnityEngine.Matrix4x4"
    mesh = "UnityEngine.Mesh"
    quaternion = "UnityEngine.Quaternion"
    vector2 = "UnityEngine.Vector2"
    vector3 = "UnityEngine.Vector3"
    vector4 = "UnityEngine.Vector4"
    texture2d = "UnityEngine.Texture2D"
    transform = "UnityEngine.Transform"


class ES2ValueType(IntEnum):
    Null = 0
    byte = 916439771
    bool = 2907536540
    string = 4259967470
    int32 = 3802662998
    float = 1849612139
    boneweight = 1899243194
    color = 852446001
    mesh = 2420697311
    matrix4x4 = 4002355558
    quaternion = 3919836870
    vector2 = 3046768853
    vector3 = 3966164038
    vector4 = 4170910408
    texture2d = 1791399917
    transform = 159054454
