# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0

import dataclasses
import enum
import io
import re
from typing import Iterator
from typing import Optional
from typing import TextIO


class TemplateError(Exception):
    """Raised when template contains error."""


class FieldKind(enum.Enum):
    """
    Enumeration defining computed fields.
    """

    YEAR = "year"


class TokenKind(enum.Enum):
    """
    Tokens read from a header template.

    The values of each enum is the regular expression pattern used to match
    that token.
    """

    NEWLINE = r"\n"
    ESCAPED = r"\\[{}\\]"
    YEAR = r"{{YEAR}}"
    INVALID = r"[{}\\]"
    CONTENT = r"."


# kind, value, row, column
Token = tuple[TokenKind, str, int, int]

_TOKENIZER_RE = re.compile("|".join(f"(?P<{t.name}>{t.value})" for t in TokenKind))

_YEAR_RE = re.compile(r"\d{4}(?:-\d{4})?")

_GROUP_YEAR_RE = re.compile(r"(\d{4})(?:-(\d{4}))?")


@dataclasses.dataclass(frozen=True, order=True)
class Years:
    """
    Year range that is written into YEAR fields.
    """

    start: int
    end: int

    def __str__(self):
        if self.start == self.end:
            return str(self.start)
        else:
            return f"{self.start}-{self.end}"

    def __iter__(self):
        yield self.start
        yield self.end


FieldValues = tuple[Years, ...]


@dataclasses.dataclass(frozen=True)
class ParsedValues:
    """
    All values parsed from a written header.

    :fields: Value of all fields from header.
    :header: The parsed header itself with all field values embedded.
    """

    fields: FieldValues
    header: str


@dataclasses.dataclass(frozen=True)
class HeaderParser:
    """
    Existing header parser.

    Derived from a header template, this class will parse an existing header
    with embedded field values and extract those values.

    :fields: Known fields as parsed from header template.
    :regex: Regular expression used to match a header at the top of a file
        and extract the fields as groups.
    """

    fields: tuple[FieldKind, ...]
    regex: re.Pattern

    def parse_fields(self, content: str) -> Optional[ParsedValues]:
        """
        Parse fields from a header.

        This parses fields from an existing header.

        :param content: Contents of whole file as read from file system.
        :return: `ParsedValues` if file has header, else None.
        """
        match = self.regex.match(content)
        if not match:
            return None
        else:
            values = []
            for group in range(1, len(self.fields) + 1):
                unparsed = match.group(group)
                year_match = _GROUP_YEAR_RE.match(unparsed)
                assert year_match is not None
                start, end = year_match.groups()
                start_int = int(start)
                end_int = int(start if end is None else end)
                values.append(Years(start_int, end_int))
            return ParsedValues(tuple(values), match.group(0))


def tokenize_template(template: str) -> Iterator[Token]:
    """
    Parse template into a sequence of tokens.

    Reads a header template and emits a sequence of tokens that describes
    the content of that header.

    Each token is a tuple of 4 values:
        token kind: A value from `TokenKind`. `TokenKind.INVALID` is never emitted.
            When an invalid token is discovered, this will cause a `TemplateError`.
        value: The raw text value of the content.

    The token stream can be used for more than one purpose. It is used to parse
    the template to build a header parser as well as re-parsing for the purposes
    of rewriting it.

    :param template:
    :return:
    """
    line = 1
    column = 1
    content = io.StringIO()
    for match in _TOKENIZER_RE.finditer(template):
        assert match.lastgroup
        kind = TokenKind[match.lastgroup]
        value = match.group(kind.name)

        if kind == TokenKind.CONTENT:
            content.write(value)
            continue

        content_value = content.getvalue()
        if content_value:
            yield TokenKind.CONTENT, content_value, line, column
            column += len(content_value)
            content = io.StringIO()

        if kind == TokenKind.INVALID:
            raise TemplateError(f"Invalid character {value!r} found at {line}:{column}")

        yield kind, value, line, column

        if kind is TokenKind.NEWLINE:
            line += 1
            column = 1
        else:
            column += len(value)

    content_value = content.getvalue()
    if content_value:
        yield TokenKind.CONTENT, content_value, line, column
        column += len(content_value)


def make_template_parser(template: str) -> HeaderParser:
    """
    Build a template parser from a header template.

    A template parser needs two things. One is a regular expression
    matching the header and its embedded fields represented as groups.
    The other is the sequence of field types found in the sequence
    of groups.

    :param template: A header template as read from configuration.
    :return:
    """
    pattern = io.StringIO()
    pattern.write("^")
    groups = []
    for kind, value, line, column in tokenize_template(template):
        if kind is TokenKind.YEAR:
            pattern.write(f"({_YEAR_RE.pattern})")
            groups.append(FieldKind.YEAR)
        elif kind is TokenKind.ESCAPED:
            pattern.write(re.escape(value[1:]))
        else:
            pattern.write(re.escape(value))
    return HeaderParser(tuple(groups), re.compile(pattern.getvalue()))


def write_header(template: str, values: FieldValues, output: TextIO):
    """
    Writes a header to output.

    Header is written based on a template as found in a `HeaderDef` and
    a sequence of values that are written into the fields matched in the
    template.

    :param template: Header template as found in `HeaderDef`.
    :param values: Sequence of field values defined in header template.
    :param output: Text output.
    """
    value_iterator = iter(values)
    for kind, value, line, column in tokenize_template(template):
        if kind is TokenKind.YEAR:
            years = next(value_iterator)
            output.write(str(years))
        elif kind is TokenKind.ESCAPED:
            output.write(value[1:])
        else:
            output.write(value)
