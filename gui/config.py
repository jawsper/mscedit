from dataclasses import dataclass, field, asdict
from pathlib import Path
import sys
import os

from ruamel.yaml import YAML

yaml = YAML()


def _default_open_file_dir():
    if sys.platform == "win32":
        open_file_dir = Path(
            os.path.expandvars("%APPDATA%/../LocalLow/Amistech/My Winter Car")
        )
    else:
        open_file_dir = Path(".")
    return str(open_file_dir.resolve())


@dataclass
class Config:
    open_file_dir: str = field(default_factory=_default_open_file_dir)
    open_files: list[str] = field(default_factory=list)


class ConfigLoader:
    @property
    def config_file_path(self) -> Path:
        if sys.platform == "win32":
            config_dir = Path(
                os.path.expandvars("%APPDATA%/../LocalLow/Amistech/My Winter Car")
            )
        else:
            config_dir = Path("~/.config").expanduser()
        return config_dir / "msceditor.yaml"

    def load(self) -> Config:
        if self.config_file_path.exists():
            with self.config_file_path.open() as f:
                _data = yaml.load(f)
                config = Config(**_data)
        else:
            config = Config()
            self.save(config)
        return config

    def save(self, config: Config):
        with self.config_file_path.open("w") as f:
            yaml.dump(asdict(config), f)
