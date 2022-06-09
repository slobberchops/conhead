# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0
#
# Created: 2022-06-06
# Updated: 2022-06-09
import os
import pathlib
import stat
import sys
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

DirEntry = Union["DirContent", str, "Perm", "Symlink"]

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


class Symlink:
    """
    Symlink entry.
    """

    ref: str

    def __init__(self, ref: str):
        self.ref = ref


class Fifo:
    """
    Unix Fifo.

    Do not attempt to use on Windows.
    """


def write_content(path: pathlib.Path, entry: DirEntry):
    """
    Write directory entry to path.

    :param path: Target path for directory entry.
    :param content: Any `DirEntry` type.
    """
    if isinstance(entry, dict):
        path.mkdir()
        for file_name, entry in entry.items():
            write_content(path / file_name, entry)
    elif isinstance(entry, str):
        content = config.deindent_string(entry)
        with open(path, "w+") as open_file:
            open_file.write(content)
    elif isinstance(entry, Perm):
        write_content(path, entry.content)
        mode = 0
        if entry.read:
            mode |= stat.S_IREAD
        if entry.write:
            mode |= stat.S_IWRITE
        os.chmod(path, mode)
    elif isinstance(entry, Symlink):
        target = path.parent / entry.ref
        is_dir = target.is_dir()
        path.symlink_to(entry.ref, target_is_directory=is_dir)
    elif isinstance(entry, Fifo):
        assert not sys.platform.startswith("win")
        os.mkfifo(path)
    elif entry is None:
        pass
    else:
        raise TypeError(f"Unexpected type: {type(entry)}")
