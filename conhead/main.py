# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0

import contextlib
import dataclasses
import datetime
import logging
import pathlib
import sys
from typing import Iterator
from typing import Optional

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


@dataclasses.dataclass
class Conhead:
    alternate_action: Optional[str] = None


def _check_and_delete_mutually_exclusive(
    ctx: click.Context, param: click.Option, value: bool
):
    ctx.ensure_object(Conhead)
    if value:
        conhead: Conhead = ctx.obj
        if conhead.alternate_action:
            assert param.name is not None
            raise click.BadOptionUsage(
                param.name, "--check and --delete are mutually exclusive", ctx
            )
        else:
            conhead.alternate_action = param.name
    return value


@click.command("conhead")
@click.argument("paths", nargs=-1, type=click.Path(exists=False), metavar="SRC")
@click.option(
    "--check",
    is_flag=True,
    default=False,
    is_eager=True,
    callback=_check_and_delete_mutually_exclusive,
    help=(
        "Runs check without adding headers or re-writing. "
        "Will still generate non zero exit code for files that "
        "are missing headers or are out of date."
    ),
)
@click.option(
    "--delete",
    is_flag=True,
    default=False,
    is_eager=True,
    callback=_check_and_delete_mutually_exclusive,
    help=(
        "Deletes any existing header from files. If no header "
        "is found, file is left unchanged."
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
def main(paths, check, delete, verbose, quiet):
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
            if delete:
                is_dirty = not result.is_headerless
            else:
                is_dirty = not result.is_up_to_date
            error |= is_dirty

            if check or not result.has_content or not is_dirty:
                continue

            assert result.header_def

            if delete:
                values = None
            else:
                if result.updated_values:
                    values = result.updated_values
                else:
                    values = tuple(
                        template.Years(now.year, now.year)
                        for _ in result.header_def.parser.fields
                    )

            assert result.content
            assert result.header_def
            error |= process.rewrite_file(
                path,
                logger,
                result.content,
                result.header_def,
                values,
                result.parsed_values,
                delete,
            )

        if error:
            sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()  # pragma: no cover
