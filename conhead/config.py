import dataclasses
import functools
import pathlib
import re
from typing import Any
from typing import Optional

import tomli

from conhead import template as template_module
from conhead import util


@dataclasses.dataclass(frozen=True, order=True)
class Years:
    start: int
    end: int

    def __iter__(self):
        yield self.start
        yield self.end


FieldValues = tuple[Years, ...]


class ConfigError(Exception):
    """Raised when there is a configuration error."""


INDENT_RE = re.compile(r"^(\s*)")

_GROUP_YEAR_RE = re.compile(r"(\d{4})(?:-(\d{4}))?")


def deindent_string(s: str):
    string_list = s.split("\n")
    shortest_lead = 1e9
    for line in string_list:
        if line.strip():
            match = INDENT_RE.match(line)
            assert match
            indent = match.group(1)
            indent_len = len(indent)
            shortest_lead = min(shortest_lead, indent_len)
    if shortest_lead == 1e9:
        shortest_lead = 0
    for index, line in enumerate(string_list):
        string_list[index] = line[shortest_lead:]
    return "\n".join(string_list)


@dataclasses.dataclass(frozen=True)
class Header:
    name: str
    template: str
    extensions: tuple[str, ...]

    @functools.cached_property
    def extensions_re(self) -> re.Pattern:
        pattern = "|".join(re.escape(e) for e in self.extensions)
        return re.compile(rf"\.(?:{pattern})$")

    @functools.cached_property
    def _template_re(self) -> template_module.TemplateRe:
        return template_module.make_template_re(self.template)

    @functools.cached_property
    def template_re(self) -> re.Pattern:
        return self._template_re[1]

    @functools.cached_property
    def field_map(self) -> util.FrozenDict[template_module.FieldKind]:
        return util.FrozenDict(self._template_re[0])

    def parse_fields(self, content: str) -> Optional[FieldValues]:
        match = self.template_re.match(content)
        if not match:
            return None
        else:
            values = []
            for group in self.field_map.keys():
                unparsed = match.group(group)
                year_match = _GROUP_YEAR_RE.match(unparsed)
                assert year_match is not None
                start, end = year_match.groups()
                start_int = int(start)
                end_int = int(start if end is None else end)
                values.append(Years(start_int, end_int))
            return tuple(values)

    @classmethod
    def from_dict(cls, name: str, dct: dict[str, Any]):
        # Template
        template = dct.pop("template", None)
        if template is None:
            raise ConfigError(f"tool.conhead.header.{name}: template is required")
        if not isinstance(template, str):
            raise ConfigError(f"tool.conhead.header.{name}: template must be str")

        # Extensions
        extensions = dct.pop("extensions", [name])

        if not (
            isinstance(extensions, list) and all(isinstance(s, str) for s in extensions)
        ):
            raise ConfigError(
                f"tool.conhead.header.{name}: extensions must be list of strings"
            )

        # Handle unexpected options
        if dct:
            unexpected = ", ".join(sorted(dct.keys()))
            raise ConfigError(f"unexpected options: {unexpected}")
        return cls(
            name=name, template=deindent_string(template), extensions=tuple(extensions)
        )


@dataclasses.dataclass(frozen=True)
class Config:
    headers: util.FrozenDict[Header]

    @functools.cached_property
    def extensions_re(self) -> Optional[re.Pattern]:
        groups = [
            rf"(?P<{header.name}>{header.extensions_re.pattern})"
            for header in self.headers.values()
        ]
        pattern = "|".join(groups)
        if pattern:
            return re.compile(pattern)
        else:
            return None

    def header_for_path(self, path: pathlib.Path) -> Optional[Header]:
        if not self.extensions_re:
            return None

        match = self.extensions_re.search(str(path))
        if match:
            group = match.lastgroup
            return self.headers[group]
        else:
            return None

    @classmethod
    def from_dict(cls, dct: dict[str, Any]) -> "Config":
        headers = {}
        headers_dct = dct.pop("header", {})
        if not isinstance(headers_dct, dict):
            raise ConfigError("tool.conhead.header must be section")
        for name, header_dct in headers_dct.items():
            if not isinstance(header_dct, dict):
                raise ConfigError(f"tool.conhead.header.{name} must be section")
            headers[name] = Header.from_dict(name, header_dct)
        unexpected_options = ", ".join(
            sorted(k for (k, v) in dct.items() if not isinstance(v, dict))
        )
        if unexpected_options:
            raise ConfigError(f"unexpected options: {unexpected_options}")
        unexpected_sections = ", ".join(
            sorted(k for (k, v) in dct.items() if isinstance(v, dict))
        )
        if unexpected_sections:
            raise ConfigError(f"unexpected sections: {unexpected_sections}")
        return Config(headers=util.FrozenDict(headers))


def find_pyproject() -> Optional[pathlib.Path]:
    current_path = pathlib.Path.cwd()
    while True:
        pyproject = current_path / "pyproject.toml"
        if pyproject.is_file():
            return pyproject
        parent = current_path.parent
        if parent == current_path:
            break
        else:
            current_path = parent
    return None


def parse() -> Optional[dict[str, Any]]:
    project_path = find_pyproject()
    if not project_path:
        return None
    with open(project_path, "rb") as project_file:
        return tomli.load(project_file)


def load() -> Optional[Config]:
    config_file = parse()
    if not config_file:
        return None
    tools = config_file.get("tool", {})
    if not isinstance(tools, dict):
        raise ConfigError("tool must be section")
    conhead = tools.get("conhead", {})
    if not isinstance(conhead, dict):
        raise ConfigError("tool.conhead must be section")
    return Config.from_dict(conhead)
