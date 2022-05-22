import dataclasses
import pathlib
import re
from typing import Any
from typing import Optional

import tomli

from conhead import util


class ConfigError(Exception):
    """Raised when there is a configuration error."""


INDENT_RE = re.compile(r"^(\s*)")


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
    template: str
    extensions: tuple[str, ...]

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
        return cls(template=deindent_string(template), extensions=tuple(extensions))


@dataclasses.dataclass(frozen=True)
class Config:
    headers: util.FrozenDict[Header]

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
