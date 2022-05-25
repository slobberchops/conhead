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
    header: Optional[config.Header]
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
    header = None
    updated_values = None
    parsed_values = None
    try:
        content = path.read_text()
    except FileNotFoundError:
        logger.error("file not found: %s", path)
        return CheckResult(up_to_date, header, updated_values, parsed_values)
    except PermissionError:
        logger.error("unreadable: %s", path)
        return CheckResult(up_to_date, header, updated_values, parsed_values)

    header = cfg.header_for_path(path)
    if not header:
        logger.error("no header def for: %s", path)
        return CheckResult(up_to_date, header, updated_values, parsed_values)

    parsed_values = header.parser.parse_fields(content)
    if parsed_values is None:
        logger.warning("missing header: %s", path)
        return CheckResult(up_to_date, header, updated_values, parsed_values)

    updated_values = tuple(
        conhead.template.Years(d.start, now.year) for d in parsed_values.fields
    )
    if updated_values != parsed_values.fields:
        logger.warning("header out of date: %s", path)
        updated_values = updated_values
        return CheckResult(up_to_date, header, updated_values, parsed_values)

    logger.info("up to date: %s", path)
    up_to_date = True
    return CheckResult(up_to_date, header, None, parsed_values)
