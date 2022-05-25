# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0

import os
import pathlib
import stat
from typing import Union

from conhead import config

DirEntry = Union["DirContent", str, "Perm"]

DirContent = dict[str, DirEntry]


class Perm:
    content: DirEntry
    read: bool
    write: bool

    def __init__(self, content: DirEntry, *, read: bool = True, write: bool = True):
        self.content = content
        self.read = read
        self.write = write


def write_content(path: pathlib.Path, content: DirEntry):
    if isinstance(content, dict):
        write_content_dir(path, content)
    elif isinstance(content, str):
        content = config.deindent_string(content)
        with open(path, "w") as open_file:
            open_file.write(content)
    elif isinstance(content, Perm):
        write_content(path, content.content)
        mode = 0
        if content.read:
            mode |= stat.S_IREAD
        if content.write:
            mode |= stat.S_IWRITE
        os.chmod(path, mode)
    elif content is None:
        pass
    else:
        raise TypeError(f"Unexpected type: {type(content)}")


def write_content_dir(path: pathlib.Path, content: DirContent) -> None:
    path.mkdir()
    for file_name, entry in content.items():
        write_content(path / file_name, entry)
