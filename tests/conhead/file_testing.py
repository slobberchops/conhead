import pathlib
from typing import Union

from conhead import config

DirEntry = Union["DirContent", str]

DirContent = dict[str, DirEntry]


def write_content(path: pathlib.Path, content: DirContent) -> None:
    path.mkdir()
    for file_name, entry in content.items():
        file_path = path / file_name
        if isinstance(entry, dict):
            write_content(file_path, entry)
        elif isinstance(entry, str):
            entry = config.deindent_string(entry)
            with open(file_path, "w") as open_file:
                open_file.write(entry)
        elif entry is None:
            pass
        else:
            raise TypeError(f"Unexpected type: {type(entry)}")
