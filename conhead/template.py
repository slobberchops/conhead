import dataclasses
import enum
import io
import re
from typing import Iterator


class TemplateError(Exception):
    """Raised when template contains error."""


class MarkKind(enum.Enum):
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


@dataclasses.dataclass
class Template:
    template: str
    regex: re.Pattern


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


TemplateRe = tuple[dict[str, MarkKind], re.Pattern]


def make_template_re(template: str) -> TemplateRe:
    pattern = io.StringIO()
    pattern.write("^")
    groups = {}
    for kind, value, line, column in tokenize_template(template):
        if kind is TokenKind.YEAR:
            group_name = f"grp{len(groups)}"
            pattern.write(f"(?P<{group_name}>{_YEAR_RE.pattern})")
            groups[group_name] = MarkKind.YEAR
        elif kind is TokenKind.ESCAPED:
            pattern.write(re.escape(value[1:]))
        else:
            pattern.write(re.escape(value))
    return groups, re.compile(pattern.getvalue())
