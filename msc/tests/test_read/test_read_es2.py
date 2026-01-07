from msc.es2.reader import ES2Reader


def test_read_file():
    with open("msc/tests/data/simple.txt", "rb") as f:
        reader = ES2Reader(f)
        data = reader.read_all()

        assert data["bool"].value is True
        assert data["byte"].value == 1
        assert data["string"].value == "hello world"
        assert data["int32"].value == 1
        assert data["float"].value == 1.0
