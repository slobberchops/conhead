# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0

import dataclasses
import functools
import pathlib
import re
from typing import Any
from typing import Optional

import tomli

from conhead import template as template_module
from conhead import util

"""
This module reads stuff from the pyproject.toml file.
"""


class ConfigError(Exception):
    """Raised when there is a configuration error."""


INDENT_RE = re.compile(r"^(\s*)")


def deindent_string(s: str):
    """
    De-indent a multi-line string.

    This enables the dubious practice (as practiced in this Python tool)
    of embedding text blocks within other configuration files that don't
    themselves support multi-line de-indentation.

    For example:

        .....def a_function():
        .........for i in range(10):
        .............print('I am de-indented')

    would become:

        def a_function():
        .....for i in range(10):
        .........print('I am de-indented')

    :param s: A multi-line string.
    :return: A multi-line string with all whitespace stripped based on the
        line with the shortest whitespace prefix.
    """
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
class HeaderDef:
    """
    Header definition.

    This configuration object is what defines a specific header which is
    applied to a set of files. The definition contains a template that
    is applied to all files that it matches. Files are matched by their
    extensions.
    """

    name: str
    template: str
    extensions: tuple[str, ...]

    @functools.cached_property
    def extensions_re(self) -> re.Pattern:
        """
        Header extensions regular expression.

        This regular expression when applied to a file name will determine
        if the file should sport the header provided by this definition.
        """
        pattern = "|".join(re.escape(e) for e in self.extensions)
        return re.compile(rf"\.(?:{pattern})$")

    @functools.cached_property
    def parser(self) -> template_module.HeaderParser:
        """
        Header parser for this header definition.
        """
        return template_module.make_template_parser(self.template)

    @classmethod
    def from_dict(cls, name: str, dct: dict[str, Any]):
        """
        Construct header definition from dictionary.

        The dictionary matches what is parsed by the `tomli` library.
        Specifically this dictionary is the set of options that comes
        from creating an option set like:

            [tools.conhead.header.<name>]
            template = "a template"

        The name is passed in as the `name` parameter and the options as
        the dictionary.

        If no `extensions` are provided, `name` is used as a default.

        :param name: Name of header definition.
        :param dct: Dictionary of options mapping to fields of this class.
        :return: An populated instance of `HeaderDef`
        """
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
    """
    Full set of header definitions as read from configuration.
    """

    header_defs: util.FrozenDict[HeaderDef]

    @functools.cached_property
    def extensions_re(self) -> Optional[re.Pattern]:
        """
        Regular expression used for matching header definition.

        This regular expression is constructed from all the extension regular
        expression from all header definitions. When applied to a file name it
        is capable of determining which header definition the file matches.
        """
        groups = [
            rf"(?P<{header.name}>{header.extensions_re.pattern})"
            for header in self.header_defs.values()
        ]
        pattern = "|".join(groups)
        if pattern:
            return re.compile(pattern)
        else:
            return None

    def header_for_path(self, path: pathlib.Path) -> Optional[HeaderDef]:
        """Look up `HeaderDef` for path."""
        if not self.extensions_re:
            return None

        match = self.extensions_re.search(str(path))
        if match:
            group = match.lastgroup
            return self.header_defs[group]
        else:
            return None

    @classmethod
    def from_dict(cls, dct: dict[str, Any]) -> "Config":
        """
        Create `Config` for all header definitions from dictionary.

        The dictionary matches what is parsed by the `tomli` library.
        Specifically this dictionary is the set of header definitions
        that comes all headers under `tools.conhead.header`:

        :param dct: Dictionary of header definitions.
        :return:
        """
        headers = {}
        headers_dct = dct.pop("header", {})
        if not isinstance(headers_dct, dict):
            raise ConfigError("tool.conhead.header must be section")
        for name, header_dct in headers_dct.items():
            if not isinstance(header_dct, dict):
                raise ConfigError(f"tool.conhead.header.{name} must be section")
            headers[name] = HeaderDef.from_dict(name, header_dct)
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
        return Config(header_defs=util.FrozenDict(headers))


def find_pyproject() -> Optional[pathlib.Path]:
    """
    Find `pyproject.toml` in parent directory of CWD.
    :return: Absolute path to `pyproject.toml` if found, else None.
    """
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
    """
    Parse `pyproject.toml`.

    :return: Returns dictionaries as parsed by `tomli` library.
    """
    project_path = find_pyproject()
    if not project_path:
        return None
    with open(project_path, "rb") as project_file:
        return tomli.load(project_file)


def load() -> Optional[Config]:
    """
    Load conhead configuration.
    :return: Populated `Config` if found, else None.
    """
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
