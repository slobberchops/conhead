# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0

import os
import pathlib
import stat
from typing import Union

from conhead import config

"""
Testing utility used to write file hierarchies to temporary directory.

In testing it is possible to specify a whole file tree using a dictionary.
The dictionary itself and all sub-dictionaries represent directories. String
values represent text files, while `None` values are ignored (these are useful
as dependency injection points).

A `Perm` object can be used for writing nodes that have their permissions
change from the default.
"""

DirEntry = Union["DirContent", str, "Perm"]

DirContent = dict[str, DirEntry]


class Perm:
    """
    Object permission wrapper.
    """

    content: DirEntry
    read: bool
    write: bool

    def __init__(self, content: DirEntry, *, read: bool = True, write: bool = True):
        self.content = content
        self.read = read
        self.write = write


def write_content(path: pathlib.Path, content: DirEntry):
    """
    Write directory entry to path.

    :param path: Target path for directory entry.
    :param content: Any `DirEntry` type.
    """
    if isinstance(content, dict):
        path.mkdir()
        for file_name, entry in content.items():
            write_content(path / file_name, entry)
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
