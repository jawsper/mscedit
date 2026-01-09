from io import BytesIO
from msc.es2.enums import ES2ValueType
from msc.es2.types import ES2Field
from msc.es2.unity import (
    Color,
    Mesh,
    MeshSettings,
    Quaternion,
    Vector3,
    Texture2D,
    Transform,
)
from msc.es2.writer import ES2Writer


def test_write_file():
    with BytesIO() as f:
        writer = ES2Writer(f)
        writer.save("byte", ES2Field.from_value_type(ES2ValueType.byte, 1))
        writer.save("bool", ES2Field.from_value_type(ES2ValueType.bool, True))
        writer.save("string", ES2Field.from_value_type(ES2ValueType.string, "hello world"))
        writer.save("int32", ES2Field.from_value_type(ES2ValueType.int32, 1))
        writer.save("float", ES2Field.from_value_type(ES2ValueType.float, 1.0))

        # writer.save("boneweight", ES2Field.from_value_type(ES2ValueType.boneweight, Color(0,0,0,0)))
        writer.save("color", ES2Field.from_value_type(ES2ValueType.color, Color(0,0,0,0)))
        writer.save("mesh", ES2Field.from_value_type(ES2ValueType.mesh, Mesh(settings=MeshSettings(b''))))
        writer.save("quaternion", ES2Field.from_value_type(ES2ValueType.quaternion, Quaternion(0,0,0,0)))
        writer.save("vector3", ES2Field.from_value_type(ES2ValueType.vector3, Vector3(0,0,0)))
        writer.save("texture2d", ES2Field.from_value_type(ES2ValueType.texture2d, Texture2D(b'')))
        writer.save("transform", ES2Field.from_value_type(ES2ValueType.transform, Transform()))
        writer.save_all()

        assert len(f.getvalue()) == 338
