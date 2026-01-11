from io import BytesIO
import shutil

import pytest

from msc.es2.reader import ES2Reader
from msc.es2.writer import ES2Writer


@pytest.mark.parametrize("filename", ["simple", "complex", "carparts", "items2", "savefile", "speedcam"])
def test_read_write_identical(filename: str):
    read_buffer = BytesIO()
    write_buffer = BytesIO()
    with open(f"msc/tests/data/{filename}.txt", "rb") as src:
        shutil.copyfileobj(src, read_buffer)

    read_buffer.seek(0)

    reader = ES2Reader(read_buffer)
    data = reader.read_all()

    read_buffer.seek(0)

    writer = ES2Writer(write_buffer)
    for key, value in data.items():
        writer.save(key, value)
    writer.save_all()

    write_buffer.seek(0)

    assert read_buffer.getvalue() == write_buffer.getvalue()
