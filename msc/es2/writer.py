from collections import OrderedDict
import struct
from typing import Any, BinaryIO


from .enums import ES2Key, ES2ValueType
from .types import (
    ES2Field,
)
from .unity import (
    Color,
    Mesh,
    Quaternion,
    Vector3,
    Texture2D,
    Transform,
)


class ES2Writer:
    def __init__(self, stream: BinaryIO):
        self.stream = stream
        self.data: dict[str, ES2Field] = OrderedDict()

    def write_bool(self, param: bool):
        self.write("?", param)

    def write_byte(self, param: int):
        self.write("B", param)

    def write_uint32(self, param: int):
        """
        Writes an unsigned 32-bit integer
        """
        self.write("I", param)

    def write_int32(self, param: int):
        """
        Writes a signed 32-bit integer
        """
        self.write("i", param)

    def write_float(self, param: float):
        self.write("f", param)

    def write_str(self, param: str):
        self.write_string(param)

    def write_string(self, param: str):
        encoded_string = param.encode("utf8")
        self._write_7bit_encoded_int(len(encoded_string))
        self.write(encoded_string)

    def _write_7bit_encoded_int(self, param: int):
        """
        Write out a 7-bit encoded integer.

        See https://github.com/microsoft/referencesource/blob/ec9fa9ae770d522a5b5f0607898044b7478574a3/mscorlib/system/io/binarywriter.cs#L414
        """
        while param >= 0x80:
            self.write_byte(param | 0x80)
            param >>= 7
        self.write_byte(param)

    def write_color(self, param: Color):
        self.write("ffff", param.r, param.g, param.b, param.a)

    def write_transform(self, param: Transform):
        self.write_byte(4)
        self.write_vector3(param.position)
        self.write_quaternion(param.rotation)
        self.write_vector3(param.scale)
        self.write_string(param.layer)

    def write_vector2(self, param: tuple[float, float]):
        self.write("ff", *param)

    def write_vector3(self, param: Vector3):
        self.write("fff", param.x, param.y, param.z)

    def write_vector4(self, param: tuple[float, float, float, float]):
        self.write("ffff", *param)

    def write_quaternion(self, param: Quaternion):
        self.write("ffff", param.x, param.y, param.z, param.w)

    def write_mesh(self, param: Mesh):
        assert param.settings is not None
        self.write(param.settings.get_bytes())
        self._write_array(ES2ValueType.vector3, param.vertices)
        self._write_array(ES2ValueType.int32, param.triangles)
        if param.settings.save_submeshes:
            self.write_int32(param.submesh_count)
            for i in range(param.submesh_count):
                self._write_array(ES2ValueType.int32, param.get_triangles(i))
        if param.settings.save_skinning:
            self._write_array(ES2ValueType.matrix4x4, param.bind_poses)
            self._write_array(ES2ValueType.boneweight, param.bone_weights)
        if param.settings.save_normals:
            self._write_array(ES2ValueType.vector3, param.normals)
        if param.settings.save_uv:
            self._write_array(ES2ValueType.vector2, param.uv)
        if param.settings.save_uv2:
            self._write_array(ES2ValueType.vector2, param.uv2)
        if param.settings.save_tangents:
            self._write_array(ES2ValueType.vector4, param.tangents)
        if param.settings.save_colors:
            self._write_array(ES2ValueType.color, param.colors32)

    def write_texture2d(self, texture: Texture2D):
        self.write_byte(6)
        self.write_int32(len(texture.image))
        self.stream.write(texture.image)
        self.write_int32(texture.filter_mode)
        self.write_int32(texture.aniso_level)
        self.write_int32(texture.wrap_mode)
        self.write_float(texture.mip_map_bias)

    def write(self, fmt, *param):
        if len(param) == 0:
            param = fmt
            if self.debug:
                print(f"write_raw(param: {param})")
            self.stream.write(param)
        else:
            if self.debug:
                print(
                    f"write_fmt(fmt: {fmt}, param: {param}, packed: {struct.pack(fmt, *param)})"
                )
            self.stream.write(struct.pack(fmt, *param))

    def _write_list(self, value_type, param):
        self.write_byte(0)
        self._write_array(value_type, param)

    def _write_array(self, value_type, param):
        self.write_int32(len(param))
        for item in param:
            self._write_type(value_type, item)

    def _write_dict(
        self, key_type: ES2ValueType, value_type: ES2ValueType, param: dict
    ):
        self.write_byte(0)
        self.write_byte(0)
        self.write_int32(len(param))
        for k, v in param.items():
            self._write_type(key_type, k)
            self._write_type(value_type, v)

    def _write_type(self, value_type: ES2ValueType, param: Any):
        func_name = f"write_{value_type.name}"
        getattr(self, func_name)(param)

    def _write_header(
        self,
        tag: str,
        collection_type: ES2Key,
        value_type: ES2ValueType,
        key_type: ES2ValueType,
    ):
        self.write_byte(ES2Key.Tag.value)
        self.write_string(tag)
        length_position = self.stream.tell()
        self.write_int32(0)

        if collection_type != ES2Key.Null:
            self.write_byte(collection_type.value)
        self.write_byte(255)
        self.write_uint32(value_type.value)
        if key_type is not None and key_type != ES2ValueType.Null:
            self.write_uint32(key_type.value)

        return length_position

    def _write_length(self, length_position):
        position = self.stream.tell()
        self.stream.seek(length_position)
        self.write_int32(position - length_position - 4)
        self.stream.seek(position)

    def _write_terminator(self):
        self.write_byte(ES2Key.Terminator.value)

    def save(self, tag: str, value: ES2Field):
        self.data[tag] = value

    def save_all(self):
        for tag, field in self.data.items():
            header, value = field.header, field.value
            self.debug = header.settings.debug
            if self.debug:
                print(type(value).__name__, tag)

            collection_type = header.collection_type
            value_type = header.value_type
            key_type = header.key_type
            length_position = self._write_header(
                tag, collection_type, value_type, key_type
            )

            match collection_type:
                case ES2Key.List:
                    self._write_list(header.value_type, value)
                case ES2Key.Dictionary:
                    self._write_dict(header.key_type, header.value_type, value)
                case ES2Key.Null:
                    self._write_type(value_type, value)
                case _:
                    print(tag)
                    raise NotImplementedError(
                        f"Collection type not implemented: {collection_type.name}"
                    )

            self._write_terminator()
            self._write_length(length_position)
