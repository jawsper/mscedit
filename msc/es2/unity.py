from dataclasses import dataclass, field
import struct


@dataclass
class Color:
    r: float
    g: float
    b: float
    a: float


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


@dataclass
class Quaternion:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 0.0


@dataclass
class Texture2D:
    image: bytes
    filter_mode: int = 0
    aniso_level: int = 0
    wrap_mode: int = 0
    mip_map_bias: float = 0.0

    def __str__(self):
        return f"Texture2D({len(self.image)} bytes)"


@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class Transform:
    position: Vector3 = field(default_factory=Vector3)
    rotation: Quaternion = field(default_factory=Quaternion)
    scale: Vector3 = field(default_factory=Vector3)
    layer: str = ""
