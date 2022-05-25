import contextlib
import datetime
import logging
import pathlib
import sys
from typing import Iterator

import click

from conhead import config
from conhead import process
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
            error |= not process.check_file(cfg, now, logger, path)

        if error:
            sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()  # pragma: no cover
