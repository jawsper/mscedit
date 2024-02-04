import struct
from typing import Any

from msc.es2.enums import ES2Collection, ES2ValueType


class ES2HeaderSettings:
    encrypt: bool
    debug: bool

    def __init__(self, encrypt: bool = False, debug: bool = False):
        self.encrypt = encrypt
        self.debug = debug


class ES2Header:
    collection_type: ES2Collection
    key_type: ES2ValueType
    value_type: ES2ValueType
    settings: ES2HeaderSettings

    def __init__(
        self,
        collection_type: ES2Collection,
        key_type: ES2ValueType,
        value_type: ES2ValueType,
        settings: ES2HeaderSettings,
    ):
        self.collection_type = collection_type
        self.key_type = key_type
        self.value_type = value_type
        self.settings = settings

    def __repr__(self):
        return f"ES2Header({self.collection_type})"


class ES2Tag:
    tag: str
    position: int
    settings_position: int
    next_tag_position: int

    def __init__(
        self,
        tag: str = "",
        position: int = 0,
        settings_position: int = 0,
        next_tag_position: int = 0,
    ):
        self.tag = tag
        self.position = position
        self.settings_position = settings_position
        self.next_tag_position = next_tag_position

    def __repr__(self):
        return f"ES2Tag({self.tag}, {self.position}, {self.settings_position}, {self.next_tag_position})"


class ES2Color:
    color: tuple[float, float, float, float]

    def __init__(self, r: float, g: float, b: float, a: float):
        self.color = (r, g, b, a)
        self.r, self.g, self.b, self.a = r, g, b, a

    def list(self):
        return [self.r, self.g, self.b, self.a]

    def __repr__(self):
        return f"ES2Color({self.r}, {self.g}, {self.b}, {self.a})"


class ES2Transform:
    position: "Vector3"
    rotation: "Quaternion"
    scale: "Vector3"
    layer: str

    def __init__(self):
        self.position = Vector3()
        self.rotation = Quaternion()
        self.scale = Vector3()
        self.layer = ""

    def __repr__(self):
        return f"ES2Transform({self.position}, {self.rotation}, {self.scale}, {self.layer})"


class ES2Field:
    header: ES2Header
    value: Any

    def __init__(self, header: ES2Header, value: Any):
        self.header = header
        self.value = value


class MeshSettings:
    def __init__(self, data: bytes):
        self.raw = data
        self.save_normals = False
        self.save_uv = False
        self.save_uv2 = False
        self.save_tangents = False
        self.save_submeshes = False
        self.save_skinning = False
        self.save_colors = False
        if len(data) >= 4:
            self.save_normals = data[0] != 0
            self.save_uv = data[1] != 0
            self.save_uv2 = data[2] != 0
            self.save_tangents = data[3] != 0
        if len(data) >= 5:
            self.save_submeshes = data[4] != 0
        if len(data) >= 6:
            self.save_skinning = data[5] != 0
        if len(data) >= 7:
            self.save_colors = data[6] != 0

    def get_bytes(self):
        return struct.pack("B", len(self.raw)) + self.raw


class Vector3:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = x, y, z

    def list(self):
        return [self.x, self.y, self.z]

    def __repr__(self):
        return f"Vector3({self.x}, {self.y}, {self.z})"


class Quaternion:
    def __init__(self, x=0.0, y=0.0, z=0.0, w=0.0):
        self.x, self.y, self.z, self.w = x, y, z, w

    def list(self):
        return [self.x, self.y, self.z, self.w]

    def __repr__(self):
        return f"Quaternion({self.x}, {self.y}, {self.z}, {self.w})"


class Mesh:
    def __init__(self):
        self.vertices = []
        self.triangles = []

        self.submesh_count = 0
        self.submeshes = {}

        self.bind_poses = []
        self.bone_weights = []

        self.normals = []

        self.uv = []
        self.uv2 = []

        self.tangents = []

        self.colors32 = []

        self.settings: MeshSettings | None = None

    def set_triangles(self, data, submesh_id):
        self.submeshes[submesh_id] = data

    def get_triangles(self, submesh_id):
        return self.submeshes[submesh_id]
