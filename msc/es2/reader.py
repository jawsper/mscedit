from collections import OrderedDict
import struct
from typing import Any, BinaryIO
import logging

from .exceptions import ES2InvalidDataException
from .enums import ES2Collection, ES2ValueType
from .types import (
    ES2Header,
    ES2HeaderSettings,
    ES2Tag,
    ES2Field,
    ES2Color,
    ES2Transform,
    Vector3,
    Quaternion,
    MeshSettings,
    Mesh,
)


class ES2Reader:
    def __init__(self, stream: BinaryIO):
        self.stream = stream
        self.current_tag = ES2Tag()

    def next(self):
        self.stream.seek(self.current_tag.next_tag_position)
        self.current_tag.position = self.stream.tell()
        try:
            b = self.read_byte()
        except EOFError:
            return False
        if b != 126:  # '~'
            raise ES2InvalidDataException(f"Encountered invalid byte '{b}' when reading next tag.")
        self.current_tag.tag = self.read_string()
        self.current_tag.next_tag_position = self.read_int() + self.stream.tell()
        self.current_tag.settings_position = self.stream.tell()
        return True

    def reset(self):
        self.stream.seek(0)
        self.current_tag = ES2Tag()

    def read_all(self) -> OrderedDict[str, ES2Field]:
        data = OrderedDict()
        self.reset()
        while self.next():
            header = self.read_header()
            if header.settings.encrypt:
                raise NotImplementedError("Cannot deal with encryption sorry.")
            match header.collection_type:
                case ES2Collection.List:
                    self.read_byte()
                    num = self.read_int()
                    val = []
                    for i in range(num):
                        val.append(self._read_type(header.value_type))
                    data[self.current_tag.tag] = val
                case ES2Collection.Dictionary:
                    self.read_byte()
                    self.read_byte()
                    val = {}
                    num = self.read_int()
                    for i in range(num):
                        k = self._read_type(header.key_type)
                        v = self._read_type(header.value_type)
                        val[k] = v
                    data[self.current_tag.tag] = val
                case ES2Collection.Null:
                    data[self.current_tag.tag] = self._read_type(header.value_type)
                case _:
                    logging.warn(f"Failed to read header collection type {header.collection_type}")

            data[self.current_tag.tag] = ES2Field(
                header, data.get(self.current_tag.tag, None)
            )
        return data

    def read_string(self):
        strlen = self.read_7bit_encoded_int()
        if strlen < 0:
            raise Exception("Invalid string")
        if strlen == 0:
            return ""
        if strlen > 127:
            # todo: implement longer strings (is it even hard?)
            raise NotImplementedError("Long strings not supported yet")
        return self.stream.read(strlen).decode("utf8")

    def read_7bit_encoded_int(self):
        num = 0
        num2 = 0
        while num2 != 35:
            b = self.read_byte()
            num |= (b & 127) << num2
            num2 += 7
            if (b & 128) == 0:
                return num
        raise Exception("Format_Bad7BitInt32")

    def read_int(self) -> int:
        return self.read("I")

    def read_byte(self) -> int:
        return self.read("B")

    def read_float(self) -> float:
        return self.read("f")

    def read_bool(self) -> bool:
        return bool(self.read_byte())

    def read_color(self):
        return ES2Color(*self.read("ffff"))

    def read_transform(self):
        transform = ES2Transform()
        for i in range(self.read_byte()):
            if i == 0:
                transform.position = self.read_vector3()
            elif i == 1:
                transform.rotation = self.read_quaternion()
            elif i == 2:
                transform.scale = self.read_vector3()
            elif i == 3:
                transform.layer = self.read_string()
        return transform

    def read_vector2(self):
        return self.read("ff")

    def read_vector3(self):
        return Vector3(*self.read("fff"))

    def read_vector4(self):
        return self.read("ffff")

    def read_quaternion(self):
        return Quaternion(*self.read("ffff"))

    def read_mesh(self):
        # print('-----read_mesh-----')
        mesh_settings_len = self.read_byte()
        mesh_settings = MeshSettings(self.stream.read(mesh_settings_len))

        mesh = Mesh()
        mesh.vertices = self._read_array(ES2ValueType.vector3)
        mesh.triangles = self._read_array(ES2ValueType.int)
        if mesh_settings.save_submeshes:
            mesh.submesh_count = self.read_int()
            for i in range(mesh.submesh_count):
                mesh.set_triangles(self._read_array(ES2ValueType.int), i)
        if mesh_settings.save_skinning:
            mesh.bind_poses = self._read_array(ES2ValueType.matrix4x4)
            mesh.bone_weights = self._read_array(ES2ValueType.boneweight)
        if mesh_settings.save_normals:
            mesh.normals = self._read_array(ES2ValueType.vector3)
        else:
            pass  # mesh.recalculate_normals
        if mesh_settings.save_uv:
            mesh.uv = self._read_array(ES2ValueType.vector2)
        if mesh_settings.save_uv2:
            mesh.uv2 = self._read_array(ES2ValueType.vector2)
        if mesh_settings.save_tangents:
            mesh.tangents = self._read_array(ES2ValueType.vector4)
        if mesh_settings.save_colors:
            mesh.colors32 = self._read_array(ES2ValueType.color)
        # print(mesh.vertices)
        # print(mesh.triangles)

        # print('-------------------')
        # print()
        mesh.settings = mesh_settings
        return mesh

    def _read_array(self, type):
        array = []
        count = self.read_int()
        for i in range(count):
            array.append(self._read_type(type))
        return array

    def _read_type(self, value_type):
        try:
            func_name = f"read_{value_type.name}"
            return getattr(self, func_name)()
        except AttributeError:
            raise NotImplementedError(f"Value type {value_type} not implemented")

    def read(self, fmt) -> Any:
        expected_size = struct.calcsize(fmt)
        data = self.stream.read(expected_size)
        if len(data) != expected_size:
            raise EOFError(
                f"Not enough bytes read, {len(data)} read, expected {expected_size}"
            )
        val = struct.unpack(fmt, data)
        if len(val) == 1:
            return val[0]
        return val

    def read_header(self):
        collection_type = ES2Collection.Null
        key_type = ES2ValueType.Null
        value_type = ES2ValueType.Null
        settings = ES2HeaderSettings(encrypt=False, debug=False)
        while True:
            b = self.read_byte()
            if b == 127:
                settings.encrypt = True
            elif b == 123:
                continue
            elif b == 255:
                if collection_type == ES2Collection.Dictionary:
                    key_type = ES2ValueType(self.read_int())
                else:
                    value_type = ES2ValueType(self.read_int())
                return ES2Header(collection_type, key_type, value_type, settings)
            elif b < 81:
                if collection_type == ES2Collection.Dictionary:
                    pass
                    # key_type = hash???
                else:
                    pass
                    # value_type = hash???
                raise NotImplementedError("Get type from key not implemented")
                return ES2Header(collection_type, key_type, value_type, settings)
            elif b >= 101:
                break
            else:
                collection_type = ES2Collection(b)
                if collection_type == ES2Collection.Dictionary:
                    b2 = self.read_byte()
                    if b2 == 255:
                        value_type = ES2ValueType(self.read_int())
                        key_type = ES2ValueType(self.read_int())
                        return ES2Header(
                            collection_type, key_type, value_type, settings
                        )
                    # value_type = hash???
                    raise NotImplemented("Get type from key not implemented")
        raise ES2InvalidDataException("Encountered invalid data when reading header.")TOD