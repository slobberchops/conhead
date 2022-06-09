# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0
#
import dataclasses
import datetime
import logging
import pathlib
from typing import Optional
from typing import Union

import click

from conhead import config
from conhead import template

"""
Higher level processing of headers on files.
"""


@dataclasses.dataclass(frozen=True)
class CheckResult:
    """
    Result from header check against single file.

    Attributes:

    :is_up_to_date: If file exists, has a header and is up to date, this is True
        else False.
    :content: Full content of parsed file.
    :header_def: `HeaderDef` configuration matched for file.
    :updated_values: Sequence of new values for out of date header. Only
        present if file already has a header and some values in that header
        are out of date.
    :parsed_values: Original values and header from files that already contain
        header.
    """

    is_up_to_date: bool
    content: Optional[str]
    header_def: Optional[config.HeaderDef]
    updated_values: Optional[template.FieldValues]
    parsed_values: Optional[template.ParsedValues]

    @property
    def has_content(self):
        return bool(self.content)

    @property
    def has_header(self):
        return bool(self.parsed_values)

    @property
    def is_headerless(self):
        return self.has_content and not self.has_header


def check_path(
    cfg: config.Config,
    now: datetime.datetime,
    logger: logging.Logger,
    path: Union[pathlib.Path, str],
    *,
    ignore_missing_template,
) -> CheckResult:
    """
    Check path to see if file exists, has header and header up to date.

    :param cfg: Full conhead configuration containing all header definitions.
    :param now: Current timestamp for purposes of updating date related fields.
    :param logger: A logger.
    :param path: Relative or absolute path.
    :return: `CheckResult` instance.
    """
    if isinstance(path, str):
        path = pathlib.Path(path)

    up_to_date = False
    content = None
    updated_values = None
    parsed_values = None

    header_def = cfg.header_for_path(path)
    if not header_def and ignore_missing_template:
        logger.debug("skipping: %s", path)
        return CheckResult(
            up_to_date, content, header_def, updated_values, parsed_values
        )

    logger.debug("checking: %s", path)
    if not header_def:
        logger.error("no header def: %s", path)
        return CheckResult(
            up_to_date, content, header_def, updated_values, parsed_values
        )

    try:
        content = path.read_text()
    except FileNotFoundError:
        logger.error("file not found: %s", path)
        return CheckResult(
            up_to_date, content, header_def, updated_values, parsed_values
        )
    except PermissionError:
        logger.error("unreadable: %s", path)
        return CheckResult(
            up_to_date, content, header_def, updated_values, parsed_values
        )
    except OSError as err:
        logger.error("%s (%s): %s", err, type(err).__name__, path)
        return CheckResult(
            up_to_date, content, header_def, updated_values, parsed_values
        )

    parsed_values = header_def.parser.parse_fields(content)
    if parsed_values is None:
        logger.warning("missing header: %s", path)
        return CheckResult(
            up_to_date, content, header_def, updated_values, parsed_values
        )

    updated_values = tuple(d.update(now) for d in parsed_values.fields)
    if updated_values != parsed_values.fields:
        logger.warning("out of date: %s", path)
        updated_values = updated_values
        return CheckResult(
            up_to_date, content, header_def, updated_values, parsed_values
        )

    logger.info("up to date: %s", path)
    up_to_date = True
    return CheckResult(up_to_date, content, header_def, None, parsed_values)


def rewrite_file(
    path: Union[pathlib.Path, str],
    logger: logging.Logger,
    content: str,
    header_def: config.HeaderDef,
    field_values: Optional[template.FieldValues],
    parsed_values: Optional[template.ParsedValues],
    remove_header: bool,
    show_changes: bool,
) -> bool:
    """
    Re-write a file based on result of previous check.

    :param path: Relative or absolute path. Any file at this path will be rewritten
        with an up to date header.
    :param logger: A logger.
    :param content: Content from file as previously read during check.
    :param header_def: Rewrite using header definition.
    :param field_values: Sequence of up to date values for rewritten header.
    :param parsed_values: Values originally parsed from matched header.
    :param remove_header: If False, will re-write file with header, else will
        omit header.
    :param show_changes: If True, show changes to file, else don't show changes.
    :return: True if header rewritten, else False.
    """
    if isinstance(path, str):
        path = pathlib.Path(path)

    if remove_header:
        logger.info("removing header: %s", path)
    else:
        logger.info("rewriting: %s", path)
    if parsed_values:
        header_len = len(parsed_values.header)
        headerless_content = content[header_len:]
    else:
        headerless_content = content

    if remove_header:
        new_header = ""
    else:
        assert field_values
        new_header = template.write_header(header_def.template, field_values)

    if show_changes:
        click.secho(path)
        if parsed_values:
            click.secho(parsed_values.header, fg="red")
        else:
            click.secho("New header", fg="red")
        click.secho("")
        if not new_header:
            click.secho("Header removed", fg="green")
        else:
            click.secho(new_header, fg="green")
        click.secho("")

    try:
        with path.open("w") as source_file:
            if new_header:
                source_file.write(new_header)
            source_file.write(headerless_content)
    except PermissionError:
        logger.error("unwritable: %s", path)
        return False
    except OSError as err:
        logger.error("%s (%s): %s", err, type(err).__name__, path)
        return False

    return True
