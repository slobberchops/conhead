import dataclasses
import datetime
import logging
import pathlib
from typing import Optional
from typing import Union

import conhead.template
from conhead import config
from conhead import template


@dataclasses.dataclass(frozen=True)
class CheckResult:
    up_to_date: bool
    content: Optional[str]
    header_def: Optional[config.HeaderDef]
    updated_values: Optional[template.FieldValues]
    parsed_values: Optional[template.ParsedValues]


def check_file(
    cfg: config.Config,
    now: datetime.datetime,
    logger: logging.Logger,
    path: Union[pathlib.Path, str],
) -> CheckResult:
    if isinstance(path, str):
        path = pathlib.Path(path)

    logger.info("process %s", path)
    up_to_date = False
    content = None
    header_def = None
    updated_values = None
    parsed_values = None
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

    header_def = cfg.header_for_path(path)
    if not header_def:
        logger.error("no header def: %s", path)
        return CheckResult(
            up_to_date, content, header_def, updated_values, parsed_values
        )

    parsed_values = header_def.parser.parse_fields(content)
    if parsed_values is None:
        logger.warning("missing header: %s", path)
        return CheckResult(
            up_to_date, content, header_def, updated_values, parsed_values
        )

    updated_values = tuple(
        conhead.template.Years(d.start, now.year) for d in parsed_values.fields
    )
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
    field_values: template.FieldValues,
    parsed_values: Optional[template.ParsedValues],
) -> bool:
    if isinstance(path, str):
        path = pathlib.Path(path)

    logger.info("rewriting: %s", path)
    if parsed_values:
        header_len = len(parsed_values.header)
        headerless_content = content[header_len:]
    else:
        headerless_content = content

    with path.open("w") as source_file:
        template.write_header(header_def.template, field_values, source_file)
        source_file.write(headerless_content)

    return True
