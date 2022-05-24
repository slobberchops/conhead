# line 1 2014

import contextlib
import pathlib
import sys
import datetime
from typing import Iterator

import click

from conhead import config
from conhead import util

import logging

@contextlib.contextmanager
def _logger() -> Iterator[logging.Logger]:
    logger = logging.getLogger('conhead')
    try:
        logger.addHandler(logging.StreamHandler())
        yield logger
    finally:
        del logger.manager.loggerDict['conhead']




@click.command("conhead")
@click.argument('paths', nargs=-1, type=click.Path(exists=False), metavar='SRC')
@click.option('--check', is_flag=True, default=False)
def main(paths, check):
    with _logger() as logger:
        if not check:
            logger.error('only --check is supported')
            sys.exit(1)

        cfg = config.load() or config.Config(headers=util.FrozenDict())
        if not cfg.headers:
            logger.error('no header configuration defined')
            sys.exit(1)

        now = datetime.datetime.now()

        error_count = 0
        for path in (pathlib.Path(p) for p in paths):
            logger.info('process %s', path)
            try:
                content = path.read_text()
            except FileNotFoundError:
                error_count += 1
                logger.error('file not found: %s', path)
            else:
                header = cfg.header_for_path(path)
                if not header:
                    error_count += 1
                    logger.error('no header def for: %s', path)
                else:
                    match = header.extensions_re.match(content)
                    if not match:
                        logger.warning('missing header: %s', path)
                        error_count += 1
                    else:
                        for group in header.mark_map.keys():
                            logging.error(group)

        if error_count > 0:
            sys.exit(1)

if __name__ == '__main__': # pragma: no cover
    main() # pragma: no cover
