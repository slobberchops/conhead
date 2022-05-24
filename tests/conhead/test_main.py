import datetime
import logging
from typing import Iterable
from typing import Iterator

import pytest

from conhead import main
from tests.conhead import file_testing


@pytest.mark.parametrize(
    "verbose,quiet,expected",
    [
        (0, 0, logging.WARNING),
        (1, 0, logging.INFO),
        (2, 0, logging.DEBUG),
        (3, 0, logging.DEBUG),
        (0, 1, logging.ERROR),
        (0, 2, logging.CRITICAL),
        (0, 3, logging.CRITICAL),
        (2, 3, logging.ERROR),
    ],
)
def test_conhead_logger(verbose, quiet, expected):
    with main.conhead_logger(verbose, quiet) as logger:
        manager = logger.manager
        assert manager.loggerDict["conhead"] == logger
        logger: logging.Logger = logger
        assert logger.level == expected
        assert len(logger.handlers) == 1
        (handler,) = logger.handlers
        assert isinstance(handler, logging.StreamHandler)
        assert isinstance(handler.formatter, logging.Formatter)
    assert "conhead" not in manager.loggerDict


def test_naive_now():
    dt = main.naive_now()
    expected = datetime.datetime.now()
    delta = datetime.timedelta(seconds=10)
    assert dt < expected + delta
    assert dt > expected - delta


class TestMain:
    @staticmethod
    @pytest.fixture
    def pyproject_toml() -> str:
        return '''
            [tool.conhead.header.header1]
            extensions = ["ext1", "ext2"]
            template = """
                # line 1 {{YEAR}}
                # line 2 {{YEAR}}
            """

            [tool.conhead.header.header2]
            extensions = ["ext3", "ext4"]
            template = """
                // line 1 {{YEAR}}
                // line 2 {{YEAR}}
            """
        '''

    @staticmethod
    @pytest.fixture
    def source_dir() -> file_testing.DirContent:
        return {
            "empty.ext1": "",
            "unmatched.unknown": "",
            "up-to-date.ext2": """\
                # line 1 2019
                # line 2 2014-2019
            """,
            "no-header.ext3": """\
                // No proper header
            """,
            "out-of-date.ext4": """\
                // line 1 2018
                // line 2 2014-2018
            """,
        }

    @staticmethod
    @pytest.fixture(autouse=True)
    def fake_time() -> Iterable[None]:
        original_now = main.naive_now
        try:

            def fake_now() -> Iterator[datetime.datetime]:
                yield datetime.datetime(2019, 10, 10)

            iterator = fake_now()
            main.naive_now = lambda: next(iterator)
            yield
        finally:
            main.naive_now = original_now

    @staticmethod
    def test_not_check(cli_runner, caplog):
        result = cli_runner.invoke(main.main, [])
        assert result.exit_code == 1

        (record,) = caplog.record_tuples
        assert record == ("conhead", logging.ERROR, "only --check is supported")

    @staticmethod
    @pytest.mark.parametrize("pyproject_toml", [None])
    def test_no_config(cli_runner, caplog):
        result = cli_runner.invoke(main.main, ["--check"])
        assert result.exit_code == 1

        (record,) = caplog.record_tuples
        assert record == (
            "conhead",
            logging.ERROR,
            "no header configuration defined",
        )

    @staticmethod
    def test_file_not_found(cli_runner, caplog):
        result = cli_runner.invoke(main.main, ["--check", "-vvv", "src/unknown.ext1"])
        assert result.exit_code == 1

        process, not_found = caplog.record_tuples
        assert process == ("conhead", logging.INFO, "process src/unknown.ext1")
        assert not_found == (
            "conhead",
            logging.ERROR,
            "file not found: src/unknown.ext1",
        )

    @staticmethod
    def test_unmatched(cli_runner, caplog):
        result = cli_runner.invoke(
            main.main, ["--check", "-vvv", "src/unmatched.unknown"]
        )
        assert result.exit_code == 1

        process, not_found = caplog.record_tuples
        assert process == ("conhead", logging.INFO, "process src/unmatched.unknown")
        assert not_found == (
            "conhead",
            logging.ERROR,
            "no header def for: src/unmatched.unknown",
        )

    @staticmethod
    def test_empty(cli_runner, caplog):
        result = cli_runner.invoke(main.main, ["--check", "-vvv", "src/empty.ext1"])
        assert result.exit_code == 1

        process, not_found = caplog.record_tuples
        assert process == ("conhead", logging.INFO, "process src/empty.ext1")
        assert not_found == (
            "conhead",
            logging.WARNING,
            "missing header: src/empty.ext1",
        )

    @staticmethod
    def test_no_header(cli_runner, caplog):
        result = cli_runner.invoke(main.main, ["--check", "-vvv", "src/no-header.ext3"])
        assert result.exit_code == 1

        process, not_found = caplog.record_tuples
        assert process == ("conhead", logging.INFO, "process src/no-header.ext3")
        assert not_found == (
            "conhead",
            logging.WARNING,
            "missing header: src/no-header.ext3",
        )

    @staticmethod
    def test_out_of_date(cli_runner, caplog):
        result = cli_runner.invoke(
            main.main, ["--check", "-vvv", "src/out-of-date.ext4"]
        )
        assert result.exit_code == 1

        process, not_found = caplog.record_tuples
        assert process == ("conhead", logging.INFO, "process src/out-of-date.ext4")
        assert not_found == (
            "conhead",
            logging.WARNING,
            "header out of date: src/out-of-date.ext4",
        )

    @staticmethod
    def test_up_to_date(cli_runner, caplog):
        result = cli_runner.invoke(
            main.main, ["--check", "-vvv", "src/up-to-date.ext2"]
        )
        assert result.exit_code == 0

        process, up_to_date = caplog.record_tuples
        assert process == ("conhead", logging.INFO, "process src/up-to-date.ext2")
        assert up_to_date == (
            "conhead",
            logging.INFO,
            "header is up to date: src/up-to-date.ext2",
        )
