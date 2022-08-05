#!/usr/bin/python3


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

