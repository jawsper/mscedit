from collections import OrderedDict
import struct

from .enums import ES2Collection, ES2ValueType


class ES2Writer:
    def __init__(self, stream):
        self.stream = stream
        self.data = OrderedDict()

    def write_bool(self, param):
        self.write('?', param)

    def write_byte(self, param):
        self.write('B', param)

    def write_int(self, param):
        self.write_int32(param)

    def write_int32(self, param):
        self.write('I', param)

    def write_float(self, param):
        self.write('f', param)

    def write_str(self, param):
        self.write_string(param)

    def write_string(self, param):
        param = param.encode('ascii')
        if len(param) > 127:
            raise NotImplementedError("Cannot write strings longer than 127 bytes.s")
        self.write_7bit_encoded_int(len(param))
        self.write(param)

    def write_7bit_encoded_int(self, param):
        self.write('B', param)

    def write_color(self, param):
        self.write('ffff', *param.color)

    def write_transform(self, param):
        # self.debug = True
        self.write_byte(4)
        self.write_vector3(param.position)
        self.write_quaternion(param.rotation)
        self.write_vector3(param.scale)
        self.write_string(param.layer)
        # self.debug = False

    def write_vector2(self, param):
        self.write('ff', *param)

    def write_vector3(self, param):
        self.write('fff', *param.list())

    def write_vector4(self, param):
        self.write('ffff', *param)

    def write_quaternion(self, param):
        self.write('ffff', *param.list())

    def write_mesh(self, param):
        # self.debug = True
        self.write(param.settings.get_bytes())
        self._write_array(ES2ValueType.vector3, param.vertices)
        self._write_array(ES2ValueType.int, param.triangles)
        if param.settings.save_submeshes:
            self.write_int32(param.submesh_count)
            for i in range(param.submesh_count):
                self._write_array(ES2ValueType.int, param.get_triangles(i))
        if param.settings.save_skinning:
            self._write_array(ES2ValueType.matrix4x4, param.bindposes)
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
                print('write_raw(param: {})'.format(param))
            self.stream.write(param)
        else:
            if self.debug:
                print('write_fmt(fmt: {}, param: {}, packed: {})'.format(fmt, param, struct.pack(fmt, *param)))
            self.stream.write(struct.pack(fmt, *param))

    def _write_list(self, value_type, param):
        self.write_byte(0)
        self._write_array(value_type, param)

    def _write_array(self, value_type, param):
        self.write_int32(len(param))
        for item in param:
            self._write_type(value_type, item)

    def _write_type(self, value_type, param):
        func_name = 'write_{}'.format(value_type.name)
        getattr(self, func_name)(param)

    def _write_header(self, tag, collection_type, value_type, key_type):
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
        for k, field in self.data.items():
            header, value = field.header, field.value
            self.debug = False
            if 'debug' in header.settings:
                self.debug = header.settings['debug']
            if self.debug:
                print(type(value).__name__, k)

            collection_type = header.collection_type
            value_type = header.value_type
            key_type = header.key_type
            length_position = self._write_header(k, collection_type, value_type, key_type)

            if collection_type == ES2Collection.List:
                self._write_list(header.value_type, value)
            else:
                func_name = 'write_' + value_type.name  # type(value).__name__
                if hasattr(self, func_name):
                    getattr(self, func_name)(value)
                else:
                    print(k)
                    raise NotImplementedError('Function not implemented: ' + func_name)

            self._write_terminator()
            self._write_length(length_position)
