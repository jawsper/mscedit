from io import BytesIO
from msc.es2.enums import ES2ValueType
from msc.es2.types import ES2Field
from msc.es2.writer import ES2Writer


def test_write_file():
    with BytesIO() as f:
        writer = ES2Writer(f)
        writer.save("bool", ES2Field.from_value_type(ES2ValueType.bool, True))
        writer.save("byte", ES2Field.from_value_type(ES2ValueType.byte, 1))
        writer.save("string", ES2Field.from_value_type(ES2ValueType.string, "hello world"))
        writer.save("int32", ES2Field.from_value_type(ES2ValueType.int32, 1))
        writer.save("float", ES2Field.from_value_type(ES2ValueType.float, 1.0))
        writer.save_all()

        assert len(f.getvalue()) > 0
