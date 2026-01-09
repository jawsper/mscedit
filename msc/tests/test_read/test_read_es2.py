from msc.es2.reader import ES2Reader

from msc.es2.unity import (
    Color,
    Mesh,
    Quaternion,
    Vector3,
    Texture2D,
    Transform,
)

def test_read_file():
    with open("msc/tests/data/simple.txt", "rb") as f:
        reader = ES2Reader(f)
        data = reader.read_all()

        assert data["bool"].value is True
        assert data["byte"].value == 1
        assert data["string"].value == "hello world"
        assert data["int32"].value == 1
        assert data["float"].value == 1.0

def test_read_complex_file():
    with open("msc/tests/data/complex.txt", "rb") as f:
        reader = ES2Reader(f)
        data = reader.read_all()

        assert data["bool"].value is True
        assert data["byte"].value == 1
        assert data["string"].value == "hello world"
        assert data["int32"].value == 1
        assert data["float"].value == 1.0

        assert isinstance(data["color"].value, Color)
        assert isinstance(data["mesh"].value, Mesh)
        assert isinstance(data["quaternion"].value, Quaternion)
        assert isinstance(data["vector3"].value, Vector3)
        assert isinstance(data["texture2d"].value, Texture2D)
        assert isinstance(data["transform"].value, Transform)
