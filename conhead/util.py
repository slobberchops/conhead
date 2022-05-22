import collections.abc
import copy


class FrozenDict(collections.abc.Mapping):
    __dict: dict

    def __init__(self, dct=None, /, **kwargs):
        self.__dict = dict(kwargs or {})
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
        if isinstance(other, collections.Mapping):  # type: ignore
            return type(self)(self.__dict | other)
        else:
            return NotImplemented

    def __ror__(self, other):
        if isinstance(other, collections.Mapping):  # type: ignore
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
