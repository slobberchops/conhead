import datetime
import logging

import pytest

from conhead import main
from tests.conhead import fixtures


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


@pytest.mark.usefixtures("fake_time")
class TestMain:
    source_dir = staticmethod(fixtures.populated_source_dir)
    pyproject_toml = staticmethod(fixtures.populated_pyproject_toml)

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
    def test_no_errors(cli_runner, caplog):
        result = cli_runner.invoke(
            main.main, ["--check", "-vvv", "src/up-to-date.ext2"]
        )
        assert result.exit_code == 0

        process, up_to_date = caplog.record_tuples
        assert process == ("conhead", logging.INFO, "process src/up-to-date.ext2")
        assert up_to_date == (
            "conhead",
            logging.INFO,
            "up to date: src/up-to-date.ext2",
        )

    @staticmethod
    def test_has_errors(cli_runner, caplog):
        result = cli_runner.invoke(
            main.main,
            ["--check", "-vvv", "src/up-to-date.ext2", "src/out-of-date.ext4"],
        )
        assert result.exit_code == 1

        process1, ok, process2, error = caplog.record_tuples
        assert process1 == ("conhead", logging.INFO, "process src/up-to-date.ext2")
        assert ok == (
            "conhead",
            logging.INFO,
            "up to date: src/up-to-date.ext2",
        )
        assert process2 == ("conhead", logging.INFO, "process src/out-of-date.ext4")
        assert error == (
            "conhead",
            logging.WARNING,
            "header out of date: src/out-of-date.ext4",
        )

    @staticmethod
    def test_quiet(cli_runner, caplog):
        result = cli_runner.invoke(
            main.main,
            ["--check", "-qqq", "src/up-to-date.ext2", "src/out-of-date.ext4"],
        )
        assert result.exit_code == 1

        assert not caplog.record_tuples
