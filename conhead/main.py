import contextlib
import datetime
import logging
import pathlib
import sys
from typing import Iterator
from typing import Union

import click

from conhead import config
from conhead import util


@contextlib.contextmanager
def conhead_logger(verbose: int, quiet: int) -> Iterator[logging.Logger]:
    logger = logging.getLogger("conhead")
    try:
        noisy = verbose - quiet
        level = logging.WARNING - noisy * 10
        level = min(logging.CRITICAL, level)
        level = max(logging.DEBUG, level)
        logger.setLevel(level)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(stream_handler)
        yield logger
    finally:
        del logger.manager.loggerDict["conhead"]


def naive_now() -> datetime.datetime:
    return datetime.datetime.now()


def process_path(
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


@click.command("conhead")
@click.argument("paths", nargs=-1, type=click.Path(exists=False), metavar="SRC")
@click.option("--check", is_flag=True, default=False)
@click.option("--verbose", "-v", count=True)
@click.option("--quiet", "-q", count=True)
def main(paths, check, verbose, quiet):
    with conhead_logger(verbose, quiet) as logger:
        if not check:
            logger.error("only --check is supported")
            sys.exit(1)

        cfg = config.load() or config.Config(headers=util.FrozenDict())
        if not cfg.headers:
            logger.error("no header configuration defined")
            sys.exit(1)

        now = naive_now()

        error = False
        for path in (pathlib.Path(p) for p in paths):
            error |= not process_path(cfg, now, logger, path)

        if error:
            sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()  # pragma: no cover
