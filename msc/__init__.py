#!/usr/bin/python3

import struct
from collections import OrderedDict
from enum import Enum, IntEnum
import shutil
import sys

class ES2InvalidDataException(Exception):
    pass

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
    Null         =  0
    transform    =  159054454
    color        =  852446001
    float        = 1849612139
    bool         = 2907536540
    int          = 3802662998
    string       = 4259967470
    mesh         = 2420697311
    quaternion   = 121        # TODO: find actual hash!
    vector2      = 122        # TODO: find actual hash!
    vector3      = 123        # TODO: find actual hash!
    vector4      = 124        # TODO: find actual hash!
    matrix4x4    = 125        # TODO: find actual hash!
    boneweight   = 126        # TODO: find actual hash!


class ES2Header:
    def __init__(self, collection_type, key_type, value_type, settings):
        self.collection_type = collection_type
        self.key_type = key_type
        self.value_type = value_type
        self.settings = settings

    def __repr__(self):
        return 'ES2Header({})'.format(self.collection_type)

class ES2Tag:
    def __init__(self, tag=None, position=None, settings_position=None, next_tag_position=None):
        if tag is None:
            self.tag = None
            self.position = 0
            self.settings_position = 0
            self.next_tag_position = 0
            self.is_null = True
        else:
            self.tag = tag
            self.position = position
            self.settings_position = settings_position
            self.next_tag_position = next_tag_position
            self.is_null = False

    def __repr__(self):
        return 'ES2Tag("{}")'.format(
            self.tag, self.position, self.settings_position, self.next_tag_position)

class ES2Color:
    def __init__(self, r, g, b, a):
        self.color = (r, g, b, a)
        self.r, self.g, self.b, self.a = r, g, b, a

    def list(self):
        return [self.r, self.g, self.b, self.a]

    def __repr__(self):
        return 'ES2Color({}, {}, {}, {})'.format(self.r, self.g, self.b, self.a)

class ES2Transform:
    def __init__(self):
        self.position = Vector3()    # Vector3
        self.rotation = Quaternion() # Quaternion
        self.scale = Vector3()       # Vector3
        self.layer = ''

    def __repr__(self):
        return 'ES2Transform({}, {}, {}, "{}")'.format(
            self.position, self.rotation, self.scale, self.layer)

class ES2Field:
    def __init__(self, header, value):
        self.header = header
        self.value = value

class MeshSettings:
    def __init__(self, data):
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
        return struct.pack('B', len(self.raw)) + self.raw

class Vector3:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = x, y, z

    def list(self):
        return [self.x, self.y, self.z]

    def __repr__(self):
        return 'Vector3({}, {}, {})'.format(*self.list())

class Quaternion:
    def __init__(self, x=0.0, y=0.0, z=0.0, w=0.0):
        self.x, self.y, self.z, self.w = x, y, z, w

    def list(self):
        return [self.x, self.y, self.z, self.w]

    def __repr__(self):
        return 'Quaternion({}, {}, {}, {})'.format(*self.list())

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

        self.settings = None

    def set_triangles(self, data, submesh_id):
        self.submeshes[submesh_id] = data

    def get_triangles(self, submesh_id):
        return self.submeshes[submesh_id]


class ES2Reader:
    def __init__(self, stream):
        self.stream = stream
        self.current_tag = ES2Tag("", 0, 0, 0)

    def next(self):
        self.stream.seek(self.current_tag.next_tag_position)
        self.current_tag.position = self.stream.tell()
        b = self.read_byte()
        if not b:
            return False
        if b != 126: # ~
            raise ES2InvalidDataException
        self.current_tag.tag = self.read_string()
        self.current_tag.next_tag_position = self.read_int() + self.stream.tell()
        self.current_tag.settings_position = self.stream.tell()
        return True

    def reset(self):
        self.stream.seek(0)
        self.current_tag = ES2Tag()

    def read_all(self):
        data = OrderedDict()
        self.reset()
        while self.next():
            header = self.read_header()
            if header.settings['encrypt']:
                raise NotImplementedError('Cannot deal with encryption sorry not sorry.')
            elif header.collection_type != ES2Collection.Null:
                if header.collection_type == ES2Collection.List:
                    self.read_byte()
                    num = self.read_int()
                    val = []
                    for i in range(num):
                        val.append(self._read_type(header.value_type))
                    data[self.current_tag.tag] = val
            else:
                data[self.current_tag.tag] = self._read_type(header.value_type)

            data[self.current_tag.tag] = ES2Field(header, data[self.current_tag.tag])
        return data

    def read_string(self):
        num2 = self.read_7bit_encoded_int()
        if num2 < 0:
            raise Exception("Invalid string")
        if num2 == 0:
            return ''
        if num2 > 127:
            raise NotImplementedError('Long strings not supported yet')
        return self.stream.read(num2).decode('ascii') # todo: implement longer strings (is it even hard?)

    def read_7bit_encoded_int(self):
        num = 0
        num2 = 0
        while num2 != 35:
            b = self.read_byte()
            num |= (b & 127) << num2
            num2 += 7
            if((b & 128) == 0):
                return num
        raise Exception("Format_Bad7BitInt32")

    def read_int(self):
        return self.read('I')

    def read_byte(self):
        return self.read('B')

    def read_float(self):
        return self.read('f')

    def read_bool(self):
        return bool(self.read_byte())

    def read_color(self):
        return ES2Color(*self.read('ffff'))

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
        return self.read('ff')
    def read_vector3(self):
        return Vector3(*self.read('fff'))
    def read_vector4(self):
        return self.read('ffff')

    def read_quaternion(self):
        return Quaternion(*self.read('ffff'))

    def read_mesh(self):
        # print('-----read_mesh-----')
        mesh_settings = MeshSettings(self.stream.read(self.read_byte()))

        mesh = Mesh()
        mesh.vertices = self._read_array(ES2ValueType.vector3)
        mesh.triangles = self._read_array(ES2ValueType.int)
        if mesh_settings.save_submeshes:
            mesh.submesh_count = self.read_int()
            for i in range(mesh.submesh_count):
                mesh.set_triangles(self._read_array(ES2ValueType.int), i)
        if mesh_settings.save_skinning:
            mesh.bindposes = self._read_array(ES2ValueType.matrix4x4)
            mesh.bone_weights = self._read_array(ES2ValueType.boneweight)
        if mesh_settings.save_normals:
            mesh.normals = self._read_array(ES2ValueType.vector3)
        else:
            pass # mesh.recalculate_normals
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
            func_name = 'read_' + value_type.name
            return getattr(self, func_name)()
        except AttributeError:
            raise NotImplementedError("Value type {} not implemented".format(value_type))

    def read(self, fmt):
        try:
            val = struct.unpack(fmt, self.stream.read(struct.calcsize(fmt)))
            if len(val) == 1:
                return val[0]
            return val
        except struct.error:
            return None

    def read_header(self):
        collection_type = ES2Collection.Null
        key_type = None
        value_type = ES2ValueType.Null
        settings = {'encrypt': False, 'debug': False}
        while True:
            b = self.read_byte()
            if b == 127:
                settings['encrypt'] = True
            elif b != 123:
                if b == 255:
                    break
                if b < 81:
                    if collection_type == ES2Collection.Dictionary:
                        pass
                        #key_type = hash???
                    else:
                        pass
                        #value_type = hash???
                    raise NotImplementedError('Dictionary not implemented')
                    return ES2Header(collection_type, key_type, value_type, settings)
                if b >= 101:
                    raise ES2InvalidDataException;
                collection_type = ES2Collection(b)
                if collection_type == ES2Collection.Dictionary:
                    b2 = self.read_byte()
                    if b2 == 255:
                        value_type = ES2ValueType(self.read_int())
                        key_type = ES2ValueType(self.read_int())
                        return ES2Header(collection_type, key_type, value_type, settings)
                    #value_type = hash???
        if collection_type == ES2Collection.Dictionary:
            key_type = ES2ValueType(self.read_int())
        else:
            value_type = ES2ValueType(self.read_int())
        return ES2Header(collection_type, key_type, value_type, settings)

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
        if(key_type != None):
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
                func_name = 'write_' + value_type.name #type(value).__name__
                if hasattr(self, func_name):
                    getattr(self, func_name)(value)
                else:
                    print(k)
                    raise NotImplementedError('Function not implemented: ' + func_name)

            self._write_terminator()
            self._write_length(length_position)


# class MSCEntry:
#     def __init__(self):
#         pass

#     def read(self, f):
#         self.reader = ES2Reader(f)

#         self.types = {
#             159054454: "transform",
#             852446001: "color",
#             1849612139: "float",
#             0xad4d7c9c: "bool",
#             3802662998: "integer",
#             4259967470: "string"
#         }

#         self.tag = self.reader.read_string()
#         self.length = self.reader.read_int()
#         self.reader.read_header()
#         print(self.tag, self.length)
#         sys.exit(0)

#         self.tag = self.get_string2(f, 0)
#         self.length = struct.unpack('I', f.read(4))[0]
#         self.data = f.read(self.length)

#         self.is_array = self.data[0] == 0x53
#         self.type = self.get_integer(2 if self.is_array else 1)
#         if(self.type in self.types):
#             self.type = self.types[self.type]
#         # else:
#         #     print('Unknown type! ', self.type)
#         # print(self.tag)
#         # print(self.type)
#         # print(self.data)
#         self.value = self.data
#         if self.is_array:
#             if self.type == 'string':
#                 array_length = self.get_uint8(7)
#                 self.value = []
#                 pos = 11
#                 for i in range(array_length):
#                     item = self.get_string(pos)
#                     self.value.append(item)
#                     pos += 1 + len(item)
#                 pass
#         else:
#             self.value = self.convert_value(6 if self.type == 'transform' else 5)

#     def next(self):
#         pass


#     def get_bool(self, pos=0):
#         return bool(self.data[pos])

#     def get_uint8(self, pos=0):
#         return struct.unpack_from('B', self.data, pos)[0]

#     def get_integer(self, pos=0):
#         return struct.unpack_from('I', self.data, pos)[0]

#     def get_float(self, pos=0):
#         return struct.unpack_from('f', self.data, pos)[0]

#     def get_color(self, pos=0):
#         r, g, b, a = struct.unpack_from('ffff', self.data, pos)
#         return r, g, b, a

#     def get_transform(self, pos=0):
#         print(self.tag)
#         print(self.data)
#         position = struct.unpack_from('fff', self.data, pos)
#         rotation = struct.unpack_from('fff', self.data, pos + 16)
#         scale = struct.unpack_from('fff', self.data, pos + 28)
#         layer = self.get_string(pos + 40)
#         return {
#             'position': position,
#             'rotation': rotation,
#             'scale': scale,
#             'layer': layer
#         }

#     def get_string(self, pos=0):
#         strlen = struct.unpack_from('B', self.data, pos)[0]
#         text = self.data[pos+1:pos+1+strlen].decode('ascii')
#         return text

#     def get_string2(self, f, pos=0):
#         strlen = int(f.read(1)[0])
#         text = f.read(strlen).decode('ascii')
#         return text

#     def convert_value(self, pos=0):
#         try:
#             func_name = 'get_' + self.type
#             if hasattr(self, func_name):
#                 return getattr(self, func_name)(pos)
#         except:
#             return None

def type_get_hash(name):
    if len(name) == 0:
        return 0
    i = len(name)
    num = i
    num2 = i & 1
    i >>= 1
    num3 = 0
    while i > 0:
        num += ord(name[num3])
        num4 = (ord(name[num3 + 1]) << 11) ^ num
        num = num << 16 ^ num4
        num3 += 2
        num += num >> 11
        i -= 1
    if num2 == 1:
        num += ord(name[num3])
        num ^= num << 11
        num += num >> 17
    num ^= num << 3
    num += num >> 5
    num ^= num << 4
    num += num >> 17
    num ^= num << 25
    return num + (num >> 6)

class MSCFile:
    def __init__(self, filename):
        self.filename = filename
        self.entries = {}
        with open(filename, 'rb') as f:
            reader = ES2Reader(f)
            self.entries = reader.read_all()

        # shutil.copyfile(filename, filename + '.bak')

        for tag, entry in self.entries.items():
            if tag.startswith('ShitWellLevel'):
                entry.value = 5.0
            if tag == 'WindshieldBroken':
                if entry.value == True:
                    entry.value = False

        with open(filename + '.out', 'wb') as f:
            writer = ES2Writer(f)
            for k, v in self.entries.items():
                writer.save(k, v)
            writer.save_all()
        # return
        taglist = list(self.entries.keys())
        taglist.sort()
        maxlen = 0
        for tag in taglist:
            if(len(tag) > maxlen):
                maxlen = len(tag)
        for tag in taglist:
            value = self.entries[tag].value
            # if not entry.is_array:
            #     continue
            print('{tag: <{maxlen}} {value}'.format(
                tag=tag, 
                maxlen=maxlen,
                value=value))#,
                #raw_value=''.join('{:02x}'.format(c) for c in entry.data)))

