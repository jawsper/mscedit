from .es2.reader import ES2Reader
from .es2.writer import ES2Writer


class MSCFile:
    def __init__(self, filename):
        self.filename = filename
        self.entries = {}
        with open(filename, "rb") as f:
            reader = ES2Reader(f)
            self.entries = reader.read_all()

        # shutil.copyfile(filename, filename + '.bak')

        for tag, entry in self.entries.items():
            if tag.startswith("ShitWellLevel"):
                entry.value = 5.0
            if tag == "WindshieldBroken":
                if entry.value is True:
                    entry.value = False

        with open(f"{filename}.out", "wb") as f:
            writer = ES2Writer(f)
            for k, v in self.entries.items():
                writer.save(k, v)
            writer.save_all()
        # return
        taglist = list(self.entries.keys())
        taglist.sort()
        maxlen = 0
        for tag in taglist:
            if len(tag) > maxlen:
                maxlen = len(tag)
        for tag in taglist:
            value = self.entries[tag].value
            # if not entry.is_array:
            #     continue
            print(
                "{tag: <{maxlen}} {value}".format(tag=tag, maxlen=maxlen, value=value)
            )
