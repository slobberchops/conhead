import dataclasses
import enum
import io
import re
from typing import Iterator


class TemplateError(Exception):
    """Raised when template contains error."""


class FieldKind(enum.Enum):
    YEAR = "year"


class TokenKind(enum.Enum):
    NEWLINE = r"\n"
    ESCAPED = r"\\[{}\\]"
    YEAR = r"{{YEAR}}"
    INVALID = r"[{}\\]"
    CONTENT = r"."


# kind, value, row, column
Token = tuple[TokenKind, str, int, int]

_TOKENIZER_RE = re.compile("|".join(f"(?P<{t.name}>{t.value})" for t in TokenKind))

_YEAR_RE = re.compile(r"\d{4}(?:-\d{4})?")


def tokenize_template(template: str) -> Iterator[Token]:
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


@dataclasses.dataclass(frozen=True)
class TemplateParser:
    fields: tuple[FieldKind, ...]
    regex: re.Pattern


def make_template_parser(template: str) -> TemplateParser:
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
    return TemplateParser(tuple(groups), re.compile(pattern.getvalue()))
