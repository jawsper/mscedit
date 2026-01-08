from collections import OrderedDict
import struct
from typing import Any, BinaryIO
import logging

from .exceptions import ES2InvalidDataException
from .enums import ES2Key, ES2ValueType
from .types import (
    ES2Header,
    ES2HeaderSettings,
    ES2Tag,
    ES2Field,
)
from .unity import (
    Color,
    MeshSettings,
    Mesh,
    Quaternion,
    Texture2D,
    Transform,
    Vector3,
)


class ES2Reader:
    def __init__(self, stream: BinaryIO):
        self.stream = stream
        self.current_tag = ES2Tag()

    def next(self) -> bool:
        self.stream.seek(self.current_tag.next_tag_position)
        self.current_tag.position = self.stream.tell()
        try:
            chunk_start_byte = self.read_byte()
        except EOFError:
            return False
        if chunk_start_byte != ES2Key.Tag.value:
            raise ES2InvalidDataException(
                f"Encountered invalid byte '{chunk_start_byte}' when reading next tag, expected '{ES2Key.Tag.value}'."
            )
        self.current_tag.tag = self.read_string()
        self.current_tag.next_tag_position = self.read_int32() + self.stream.tell()
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
                case ES2Key.List:
                    self.read_byte()  # always zero
                    list_len = self.read_int32()
                    val = []
                    for _ in range(list_len):
                        val.append(self._read_type(header.value_type))
                    data[self.current_tag.tag] = val
                case ES2Key.Dictionary:
                    self.read_byte()  # always zero
                    self.read_byte()  # always zero
                    val = {}
                    dictionary_len = self.read_int32()
                    for _ in range(dictionary_len):
                        k = self._read_type(header.key_type)
                        v = self._read_type(header.value_type)
                        val[k] = v
                    data[self.current_tag.tag] = val
                case ES2Key.Null:
                    data[self.current_tag.tag] = self._read_type(header.value_type)
                case _:
                    logging.warning(
                        f"Failed to read header collection type {header.collection_type}"
                    )

            data[self.current_tag.tag] = ES2Field(
                header, data.get(self.current_tag.tag, None)
            )
        return data

    def read_string(self) -> str:
        strlen = self._read_7bit_encoded_int()
        if strlen < 0:
            raise Exception("Invalid string")
        if strlen == 0:
            return ""
        return self.stream.read(strlen).decode("utf8")

    def _read_7bit_encoded_int(self) -> int:
        """
        Read a 7-bit encoded integer.

        This is a data structure that allows for storing integers in a way that smaller numbers take less space.

        Rewrote in pythonic style based on:
        https://github.com/microsoft/referencesource/blob/ec9fa9ae770d522a5b5f0607898044b7478574a3/mscorlib/system/io/binaryreader.cs#L582
        """
        str_len = 0
        # Read no more than 5 bytes, moving 7 bits at a time
        for shift in range(0, 5 * 7, 7):
            b = self.read_byte()
            str_len = (b & 127) << shift
            if (b & 128) == 0:
                return str_len
        raise ValueError("Invalid value for 7-bit encoded string length.")

    def read_int(self) -> int:
        """
        Reads an UNSIGNED integer

        :return: The value read from the stream
        :rtype: int
        """
        return self.read_uint32()

    def read_uint32(self) -> int:
        return self.read("I")

    def read_int32(self) -> int:
        return self.read("i")

    def read_byte(self) -> int:
        return self.read("B")

    def read_float(self) -> float:
        return self.read("f")

    def read_bool(self) -> bool:
        return bool(self.read_byte())

    def read_color(self):
        return Color(*self.read("ffff"))

    def read_transform(self):
        transform = Transform()
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

    def read_vector2(self) -> tuple[float, float]:
        return self.read("ff")

    def read_vector3(self):
        return Vector3(*self.read("fff"))

    def read_vector4(self) -> tuple[float, float, float, float]:
        return self.read("ffff")

    def read_quaternion(self):
        return Quaternion(*self.read("ffff"))

    def read_mesh(self):
        # print('-----read_mesh-----')
        mesh_settings_len = self.read_byte()
        mesh_settings = MeshSettings(self.stream.read(mesh_settings_len))

        mesh = Mesh()
        mesh.vertices = self._read_array(ES2ValueType.vector3)
        mesh.triangles = self._read_array(ES2ValueType.int32)
        if mesh_settings.save_submeshes:
            mesh.submesh_count = self.read_int32()
            for submesh_id in range(mesh.submesh_count):
                mesh.set_triangles(self._read_array(ES2ValueType.int32), submesh_id)
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

    def read_texture2d(self):
        texture = None
        num = self.read_byte()
        if num >= 0:
            data_length = self.read_int32()
            texture = Texture2D(self.stream.read(data_length))
        if num >= 1:
            texture.filter_mode = self.read_int32()
        if num >= 2:
            texture.aniso_level = self.read_int32()
        if num >= 3:
            texture.wrap_mode = self.read_int32()
        if num >= 4:
            texture.mip_map_bias = self.read_float()
        return texture

    def _read_array(self, type: ES2ValueType):
        array = []
        count = self.read_int32()
        for _ in range(count):
            array.append(self._read_type(type))
        return array

    def _read_type(self, value_type: ES2ValueType):
        try:
            func_name = f"read_{value_type.name}"
            func = getattr(self, func_name)
        except AttributeError:
            raise NotImplementedError(f"Value type {value_type} not implemented")
        return func()

    def read(self, fmt: str) -> Any:
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

    def read_header(self) -> ES2Header:
        collection_type = ES2Key.Null
        key_type = ES2ValueType.Null
        value_type = ES2ValueType.Null
        settings = ES2HeaderSettings(encrypt=False, debug=False)
        while True:
            b = self.read_byte()
            if b == ES2Key.Encrypt.value:
                settings.encrypt = True
            elif b == ES2Key.Terminator.value:
                continue
            elif b == 255:  # byte.MaxValue
                if collection_type == ES2Key.Dictionary:
                    key_type = ES2ValueType(self.read_uint32())
                else:
                    value_type = ES2ValueType(self.read_uint32())
                return ES2Header(collection_type, key_type, value_type, settings)
            elif b < 81:
                if collection_type == ES2Key.Dictionary:
                    pass
                    # key_type = hash???
                else:
                    pass
                    # value_type = hash???
                raise NotImplementedError("Get type from key not implemented")
                return ES2Header(collection_type, key_type, value_type, settings)
            elif b >= 101:
                break
            elif b == ES2Key.Dictionary.value:
                collection_type = ES2Key(b)
                if collection_type == ES2Key.Dictionary:
                    b2 = self.read_byte()
                    if b2 == 255:  # byte.MaxValue
                        value_type = ES2ValueType(self.read_uint32())
                        key_type = ES2ValueType(self.read_uint32())
                        return ES2Header(
                            collection_type, key_type, value_type, settings
                        )
                    # value_type = hash???
                    raise NotImplementedError("Get type from key not implemented")
        raise ES2InvalidDataException("Encountered invalid data when reading header.")
