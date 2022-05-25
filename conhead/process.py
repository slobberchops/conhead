import dataclasses
import datetime
import logging
import pathlib
from typing import Optional
from typing import Union

import conhead.template
from conhead import config
from conhead import template


@dataclasses.dataclass
class CheckResult:
    up_to_date: bool = False
    updated_values: Optional[template.FieldValues] = None
    header: Optional[config.Header] = None


def check_file(
    cfg: config.Config,
    now: datetime.datetime,
    logger: logging.Logger,
    path: Union[pathlib.Path, str],
) -> CheckResult:
    if isinstance(path, str):
        path = pathlib.Path(path)

    logger.info("process %s", path)
    result = CheckResult()
    try:
        content = path.read_text()
    except FileNotFoundError:
        logger.error("file not found: %s", path)
        return result
    except PermissionError:
        logger.error("unreadable: %s", path)
        return result

    result.header = cfg.header_for_path(path)
    if not result.header:
        logger.error("no header def for: %s", path)
        return result

    field_values = result.header.parser.parse_fields(content)
    if field_values is None:
        logger.warning("missing header: %s", path)
        return result

    updated_values = tuple(
        conhead.template.Years(d.start, now.year) for d in field_values
    )
    if updated_values != field_values:
        logger.warning("header out of date: %s", path)
        result.updated_values = updated_values
        return result

    logger.info("up to date: %s", path)
    result.up_to_date = True
    return result
