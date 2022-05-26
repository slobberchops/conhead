# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0

import contextlib
import datetime
import logging
import pathlib
import sys
from typing import Iterator

import click

from conhead import config
from conhead import process
from conhead import template
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
@click.option(
    "--check",
    is_flag=True,
    default=False,
    help=(
        "Runs check without adding headers or re-writing. "
        "Will still generate non zero exit code for files that "
        "are missing headers or are out of date."
    ),
)
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase log verbosity. May be used more than once.",
)
@click.option(
    "--quiet",
    "-q",
    count=True,
    help="Decrease log verbosity. May be used more than once.",
)
def main(paths, check, verbose, quiet):
    """
    Consistent header manager

    Maintains consistent header files across files. Adds headers to
    files that are missing them. Keeps information in header up to date
    for files that already have them.
    """
    with conhead_logger(verbose, quiet) as logger:
        cfg = config.load() or config.Config(header_defs=util.FrozenDict())
        if not cfg.header_defs:
            logger.error("no header configuration defined")
            sys.exit(1)

        now = naive_now()

        error = False
        for path in (pathlib.Path(p) for p in paths):
            result = process.check_path(cfg, now, logger, path)
            error |= not result.up_to_date
            if check or result.up_to_date or not result.header_def:
                continue

            if result.updated_values:
                values = result.updated_values
            else:
                values = tuple(
                    template.Years(now.year, now.year)
                    for _ in result.header_def.parser.fields
                )

            assert result.content
            error |= process.rewrite_file(
                path,
                logger,
                result.content,
                result.header_def,
                values,
                result.parsed_values,
            )

        if error:
            sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()  # pragma: no cover
