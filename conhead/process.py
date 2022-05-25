import datetime
import logging
import pathlib
from typing import Union

from conhead import config


def check_file(
    cfg: config.Config,
    now: datetime.datetime,
    logger: logging.Logger,
    path: Union[pathlib.Path, str],
) -> bool:
    if isinstance(path, str):
        path = pathlib.Path(path)

    logger.info("process %s", path)
    try:
        content = path.read_text()
    except FileNotFoundError:
        logger.error("file not found: %s", path)
        return False
    except PermissionError:
        logger.error("unreadable: %s", path)
        return False

    header = cfg.header_for_path(path)
    if not header:
        logger.error("no header def for: %s", path)
        return False

    mark_data = header.parse_marks(content)
    if mark_data is None:
        logger.warning("missing header: %s", path)
        return False

    updated_dates = tuple((d[0], now.year) for d in mark_data)
    if updated_dates != mark_data:
        logger.warning("header out of date: %s", path)
        return False

    logger.info("up to date: %s", path)
    return True
