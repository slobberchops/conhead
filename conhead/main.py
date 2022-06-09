# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0
#
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


def iter_dir(dir: pathlib.Path) -> Iterator[pathlib.Path]:
    for entry in sorted(dir.iterdir()):
        if entry.is_symlink():
            continue
        if entry.is_dir():
            yield from iter_dir(entry)
        elif entry.is_file():
            yield entry


def iter_path(path: pathlib.Path) -> Iterator[tuple[pathlib.Path, bool]]:
    if not path.is_dir():
        yield path, True
    else:
        for entry in iter_dir(path):
            yield entry, False


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
    "config_path",
    "--config",
    "-C",
    default=None,
    type=str,
    help="Alternate location for configuration file",
)
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase log verbosity. May be used more than once.",
)
@click.option(
    "--show-changes",
    is_flag=True,
    default=False,
    is_eager=True,
    help="Show changes in header.",
)
@click.option(
    "--quiet",
    "-q",
    count=True,
    help="Decrease log verbosity. May be used more than once.",
)
def main(paths, check, delete, config_path, verbose, show_changes, quiet):
    """
    Consistent header manager

    Maintains consistent header files across files. Adds headers to
    files that are missing them. Keeps information in header up to date
    for files that already have them.
    """
    with conhead_logger(verbose, quiet) as logger:
        try:
            if config_path is None:
                cfg = config.load_from_pyproject()
                if cfg is None:
                    logger.error("pyproject.toml not found")
                    sys.exit(1)
            else:
                cfg = config.load(pathlib.Path(config_path))
        except OSError as err:
            logger.error(f"Unable read configuration: {err}")
            sys.exit(1)
        if not cfg.header_defs:
            logger.error("no header configuration defined")
            sys.exit(1)

        now = naive_now()

        paths = paths or ["."]

        error = False
        for path_param in (pathlib.Path(p) for p in paths):
            for path, is_param in iter_path(path_param):
                result = process.check_path(
                    cfg, now, logger, path, ignore_missing_template=not is_param
                )

                # Ignore files that are found by searching a directory
                # but are not handled by any template.
                if not (result.header_def or is_param):
                    continue

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
                            f.type.new(now) for f in result.header_def.parser.fields
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
                    show_changes,
                )

        if error:
            sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()  # pragma: no cover
