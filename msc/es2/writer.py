from collections import OrderedDict
import struct
from typing import Any, BinaryIO

from msc.es2.types import ES2Color, ES2Field, ES2Transform, Mesh, Quaternion, Vector3

from .enums import ES2Collection, ES2ValueType


class ES2Writer:
    def __init__(self, stream: BinaryIO):
        self.stream = stream
        self.data = OrderedDict()

    def write_bool(self, param: bool):
        self.write("?", param)

    def write_byte(self, param: int):
        self.write("B", param)

    def write_int(self, param: int):
        self.write_int32(param)

    def write_int32(self, param: int):
        self.write("I", param)

    def write_float(self, param: float):
        self.write("f", param)

    def write_str(self, param: str):
        self.write_string(param)

    def write_string(self, param):
        param = param.encode("ascii")
        if len(param) > 127:
            raise NotImplementedError("Cannot write strings longer than 127 bytes.")
        self.write_7bit_encoded_int(len(param))
        self.write(param)

    def write_7bit_encoded_int(self, param: int):
        self.write("B", param)

    def write_color(self, param: ES2Color):
        self.write("ffff", *param.color)

    def write_transform(self, param: ES2Transform):
        # self.debug = True
        self.write_byte(4)
        self.write_vector3(param.position)
        self.write_quaternion(param.rotation)
        self.write_vector3(param.scale)
        self.write_string(param.layer)
        # self.debug = False

    def write_vector2(self, param):
        self.write("ff", *param)

    def write_vector3(self, param: Vector3):
        self.write("fff", *param.list())

    def write_vector4(self, param):
        self.write("ffff", *param)

    def write_quaternion(self, param: Quaternion):
        self.write("ffff", *param.list())

    def write_mesh(self, param: Mesh):
        # self.debug = True
        assert param.settings != None
        self.write(param.settings.get_bytes())
        self._write_array(ES2ValueType.vector3, param.vertices)
        self._write_array(ES2ValueType.int, param.triangles)
        if param.settings.save_submeshes:
            self.write_int32(param.submesh_count)
            for i in range(param.submesh_count):
                self._write_array(ES2ValueType.int, param.get_triangles(i))
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

        # self.debug = False

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

    def _write_type(self, value_type: ES2ValueType, param: Any):
        func_name = f"write_{value_type.name}"
        getattr(self, func_name)(param)

    def _write_header(
        self,
        tag: str,
        collection_type: ES2Collection,
        value_type: ES2ValueType,
        key_type: ES2ValueType,
    ):
        self.write_byte(126)
        self.write_string(tag)
        length_position = self.stream.tell()
        self.write_int32(0)

        if collection_type != ES2Collection.Null:
            self.write_byte(collection_type.value)
        self.write_byte(255)
        self.write_int32(value_type)
        if key_type is not None:
            self.write_int32(key_type)

        return length_position

    def _write_length(self, length_position):
        position = self.stream.tell()
        self.stream.seek(length_position)
        self.write_int32(position - length_position - 4)
        self.stream.seek(position)

    def _write_terminator(self):
        self.write_byte(123)

    def save(self, key, value):
        self.data[key] = value

    def save_all(self):
        field: ES2Field
        for k, field in self.data.items():
            header, value = field.header, field.value
            self.debug = header.settings.debug
            if self.debug:
                print(type(value).__name__, k)

            collection_type = header.collection_type
            value_type = header.value_type
            key_type = header.key_type
            length_position = self._write_header(
                k, collection_type, value_type, key_type
            )

            if collection_type == ES2Collection.List:
                self._write_list(header.value_type, value)
            else:
                func_name = f"write_{value_type.name}"  # type(value).__name__
                if hasattr(self, func_name):
                    getattr(self, func_name)(value)
                else:
                    print(k)
                    raise NotImplementedError(f"Function not implemented: {func_name}")

            self._write_terminator()
            self._write_length(length_position)
