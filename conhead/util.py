# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0

import collections.abc
import copy
from typing import Mapping
from typing import Optional
from typing import TypeVar

A = TypeVar("A")


class FrozenDict(collections.abc.Hashable, collections.abc.Mapping[str, A]):
    """
    A read-only dictionary capable of being hashed.
    """

    __dict: dict[str, A]

    def __init__(self, dct: Optional[Mapping[str, A]] = None, /, **kwargs):
        self.__dict = {}
        self.__dict.update(kwargs)
        if dct is not None:
            self.__dict.update(dct)

    def __len__(self):
        return len(self.__dict)

    def __getitem__(self, key):
        return self.__dict[key]

    def __iter__(self):
        return iter(self.__dict)

    def __contains__(self, key):
        return key in self.__dict

    def __repr__(self):
        return repr(self.__dict)

    def __or__(self, other):
        if isinstance(other, collections.abc.Mapping):  # type: ignore
            return type(self)(self.__dict | other)
        else:
            return NotImplemented

    def __ror__(self, other):
        if isinstance(other, collections.abc.Mapping):  # type: ignore
            return type(self)(other | self.__dict)
        else:
            return NotImplemented

    def __copy__(self):
        cp = type(self)(self)
        return cp

    def copy(self):
        return copy.copy(self)

    def __hash__(self):
        return hash(tuple(self.items()))
