# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0
#
import abc
import dataclasses
import datetime
import re
from typing import ClassVar
from typing import Generic
from typing import TypeVar

T = TypeVar("T", bound="Field")


@dataclasses.dataclass(frozen=True, order=True)
class Field(Generic[T], abc.ABC):
    name: ClassVar[str]
    regex: ClassVar[str]

    @classmethod
    @abc.abstractmethod
    def parse(cls, group_value: str) -> T:
        ...  # pragma: no cover

    @classmethod
    @abc.abstractmethod
    def new(cls, now: datetime.datetime) -> T:
        ...  # pragma: no cover

    def update(self, now: datetime.datetime) -> T:
        ...  # pragma: no cover


_GROUP_YEAR_RE = re.compile(r"^(\d{4})(?:-(\d{4}))?$")


@dataclasses.dataclass(frozen=True, order=True)
class Years(Field["Years"]):

    start: int
    end: int

    name = "YEARS"
    regex = r"\d{4}(?:-\d{4})?"

    def __str__(self):
        if self.start == self.end:
            return str(self.start)
        else:
            return f"{self.start}-{self.end}"

    def __iter__(self):
        yield self.start
        yield self.end

    @classmethod
    def parse(cls, group_value: str) -> "Years":
        match = _GROUP_YEAR_RE.match(group_value)
        if not match:
            raise ValueError(f"cannot parse years: {group_value!r}")
        start = int(match.group(1))
        unparsed_end = match.group(2)
        if unparsed_end:
            end = int(unparsed_end)
        else:
            end = start
        return cls(start, end)

    @classmethod
    def new(cls, now: datetime.datetime) -> "Years":
        return cls(now.year, now.year)

    def update(self, now: datetime.datetime) -> "Years":
        return type(self)(self.start, now.year)


_DATE_FORMAT = "%Y-%m-%d"


@dataclasses.dataclass(frozen=True, order=True)
class Date(Field["Date"]):

    date: datetime.date

    name = "DATE"
    regex = "[0-9]{4}-[0-9]{2}-[0-9]{2}"

    def __str__(self):
        return self.date.strftime(_DATE_FORMAT)

    @classmethod
    def parse(cls, group_value: str) -> "Date":
        dt = datetime.datetime.strptime(group_value, _DATE_FORMAT)
        return cls(dt.date())

    @classmethod
    def new(cls, now: datetime.datetime) -> "Date":
        return cls(now.date())

    def update(self, now: datetime.datetime) -> "Date":
        return self.new(now)
