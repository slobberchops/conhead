# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0
#
import dataclasses
import enum
import io
import re
from typing import Generic
from typing import Iterator
from typing import Optional
from typing import TypeVar
from typing import cast

from conhead import fields


class TemplateError(Exception):
    """Raised when template contains error."""


class FieldKind(enum.Enum):
    """
    Enumeration defining computed fields.
    """

    DATE = fields.Date
    YEARS = fields.Years

    @property
    def type(self) -> type[fields.Field]:
        return self.value


class TokenKind(enum.Enum):
    """
    Tokens read from a header template.

    The values of each enum is the regular expression pattern used to match
    that token.
    """

    NEWLINE = r"\n"
    ESCAPED = r"\\[{}\\]"
    FIELD = r"{{[^}]+}}"
    INVALID = r"[{}\\]"
    CONTENT = r"."


T = TypeVar("T")


class Token(Generic[T]):
    @property
    def kind(self) -> TokenKind:
        return self.__kind

    @property
    def unparsed(self) -> str:
        return self.__unparsed

    @property
    def row(self) -> int:
        return self.__row

    @property
    def column(self) -> int:
        return self.__column

    @property
    def parsed(self) -> T:
        return self.__parsed

    def __init__(
        self, kind: TokenKind, unparsed: str, row: int, column: int, parsed: T
    ):
        self.__kind = kind
        self.__unparsed = unparsed
        self.__row = row
        self.__column = column
        self.__parsed = parsed

    def __repr__(self):
        return (
            f"<token:{self.kind.name} "
            f"{self.unparsed!r} {self.row}:{self.column} "
            f"{self.parsed}>"
        )

    def __eq__(self, other):
        if isinstance(other, Token):
            return (self.kind, self.unparsed, self.row, self.column, self.parsed) == (
                other.kind,
                other.unparsed,
                other.row,
                other.column,
                other.parsed,
            )
        else:
            return NotImplemented


_TOKENIZER_RE = re.compile("|".join(f"(?P<{t.name}>{t.value})" for t in TokenKind))

_FIELD_RE = re.compile(r"{{(.*)}}")


FieldValues = tuple[fields.Field, ...]


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
            for index, field_kind in enumerate(self.fields):
                field_type = field_kind.type
                unparsed = match.group(index + 1)
                values.append(field_type.parse(unparsed))
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
            yield Token(TokenKind.CONTENT, content_value, line, column, content_value)
            column += len(content_value)
            content = io.StringIO()

        if kind == TokenKind.INVALID:
            raise TemplateError(f"Invalid character {value!r} found at {line}:{column}")

        if kind == TokenKind.ESCAPED:
            parsed_value = value[1:]
        elif kind == TokenKind.FIELD:
            field_match = _FIELD_RE.match(value)
            assert field_match
            field_kind_name = field_match.group(1)
            try:
                field_kind = FieldKind[field_kind_name]
            except KeyError:
                raise TemplateError(
                    f"Unknown field type {field_kind_name!r} at {line}:{column}"
                )
            else:
                parsed_value = cast(type[fields.Field], field_kind)
        else:
            parsed_value = value

        yield Token(kind, value, line, column, parsed_value)

        if kind is TokenKind.NEWLINE:
            line += 1
            column = 1
        else:
            column += len(value)

    content_value = content.getvalue()
    if content_value:
        yield Token(TokenKind.CONTENT, content_value, line, column, content_value)
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
    for token in tokenize_template(template):
        kind = token.kind
        if kind is TokenKind.FIELD:
            field_kind = cast(FieldKind, token.parsed)
            field_type = field_kind.type
            pattern.write(f"({field_type.regex})")
            groups.append(field_kind)
        else:
            pattern.write(re.escape(token.parsed))
    return HeaderParser(tuple(groups), re.compile(pattern.getvalue()))


def write_header(template: str, values: FieldValues) -> str:
    """
    Writes a header to output.

    Header is written based on a template as found in a `HeaderDef` and
    a sequence of values that are written into the fields matched in the
    template.

    :param template: Header template as found in `HeaderDef`.
    :param values: Sequence of field values defined in header template.
    :returns: New header as string.
    """
    header = []
    value_iterator = iter(values)
    for token in tokenize_template(template):
        kind = token.kind
        if kind is TokenKind.FIELD:
            field_value = next(value_iterator)
            header.append(str(field_value))
        else:
            header.append(token.parsed)
    return "".join(header)
