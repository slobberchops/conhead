import datetime
import logging
import pathlib
from typing import Optional
from typing import Union

import conhead.template
from conhead import config
from conhead import template


def check_file(
    cfg: config.Config,
    now: datetime.datetime,
    logger: logging.Logger,
    path: Union[pathlib.Path, str],
) -> tuple[bool, Optional[template.FieldValues]]:
    if isinstance(path, str):
        path = pathlib.Path(path)

    logger.info("process %s", path)
    try:
        content = path.read_text()
    except FileNotFoundError:
        logger.error("file not found: %s", path)
        return False, None
    except PermissionError:
        logger.error("unreadable: %s", path)
        return False, None

    header = cfg.header_for_path(path)
    if not header:
        logger.error("no header def for: %s", path)
        return False, None

    field_values = header.parser.parse_fields(content)
    if field_values is None:
        logger.warning("missing header: %s", path)
        return False, None

    updated_dates = tuple(
        conhead.template.Years(d.start, now.year) for d in field_values
    )
    if updated_dates != field_values:
        logger.warning("header out of date: %s", path)
        return False, updated_dates

    logger.info("up to date: %s", path)
    return True, None
