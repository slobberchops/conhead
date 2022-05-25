import datetime
import logging
from typing import Iterator

import pytest

import conhead.process
from conhead import template
from tests.conhead import fixtures

NOW = datetime.datetime(2019, 10, 10)

pyproject_toml = fixtures.populated_pyproject_toml
source_dir = fixtures.populated_source_dir


@pytest.mark.usefixtures("fake_time")
class TestCheckFile:
    @staticmethod
    @pytest.fixture
    def logger() -> Iterator[logging.Logger]:
        logger = logging.getLogger("test")
        try:
            logger.setLevel(logging.DEBUG)
            yield logger
        finally:
            del logger.manager.loggerDict["test"]

    @staticmethod
    def test_file_not_found(logger, conhead_config, caplog):
        result = conhead.process.check_file(
            conhead_config, NOW, logger, "src/unknown.ext1"
        )
        assert not result.up_to_date
        assert result.updated_values is None
        assert result.header_def is None

        process, not_found = caplog.record_tuples
        assert process == ("test", logging.INFO, "process src/unknown.ext1")
        assert not_found == (
            "test",
            logging.ERROR,
            "file not found: src/unknown.ext1",
        )

    @staticmethod
    def test_not_readable(logger, conhead_config, caplog):
        result = conhead.process.check_file(
            conhead_config, NOW, logger, "src/unreadable.ext1"
        )
        assert not result.up_to_date
        assert result.updated_values is None
        assert result.header_def is None

        process, not_found = caplog.record_tuples
        assert process == ("test", logging.INFO, "process src/unreadable.ext1")
        assert not_found == (
            "test",
            logging.ERROR,
            "unreadable: src/unreadable.ext1",
        )

    @staticmethod
    def test_unmatched(conhead_config, logger, caplog):
        result = conhead.process.check_file(
            conhead_config, NOW, logger, "src/unmatched.unknown"
        )
        assert not result.up_to_date
        assert result.updated_values is None
        assert result.header_def is None

        process, not_found = caplog.record_tuples
        assert process == ("test", logging.INFO, "process src/unmatched.unknown")
        assert not_found == (
            "test",
            logging.ERROR,
            "no header def for: src/unmatched.unknown",
        )

    @staticmethod
    def test_empty(conhead_config, logger, caplog):
        result = conhead.process.check_file(
            conhead_config, NOW, logger, "src/empty.ext1"
        )
        assert not result.up_to_date
        assert result.updated_values is None
        assert result.header_def is conhead_config.header_defs["header1"]

        process, not_found = caplog.record_tuples
        assert process == ("test", logging.INFO, "process src/empty.ext1")
        assert not_found == (
            "test",
            logging.WARNING,
            "missing header: src/empty.ext1",
        )

    @staticmethod
    def test_no_header(conhead_config, logger, caplog):
        result = conhead.process.check_file(
            conhead_config, NOW, logger, "src/no-header.ext3"
        )
        assert not result.up_to_date
        assert result.updated_values is None
        assert result.header_def is conhead_config.header_defs["header2"]

        process, not_found = caplog.record_tuples
        assert process == ("test", logging.INFO, "process src/no-header.ext3")
        assert not_found == (
            "test",
            logging.WARNING,
            "missing header: src/no-header.ext3",
        )

    @staticmethod
    def test_out_of_date(conhead_config, logger, caplog):
        result = conhead.process.check_file(
            conhead_config, NOW, logger, "src/out-of-date.ext4"
        )
        assert not result.up_to_date
        assert result.updated_values
        years1, years2 = result.updated_values
        assert years1 == template.Years(2018, 2019)
        assert years2 == template.Years(2014, 2019)
        assert result.header_def is conhead_config.header_defs["header2"]

        process, not_found = caplog.record_tuples
        assert process == ("test", logging.INFO, "process src/out-of-date.ext4")
        assert not_found == (
            "test",
            logging.WARNING,
            "header out of date: src/out-of-date.ext4",
        )

    @staticmethod
    def test_up_to_date(conhead_config, logger, caplog):
        result = conhead.process.check_file(
            conhead_config, NOW, logger, "src/up-to-date.ext2"
        )
        assert result.up_to_date
        assert result.updated_values is None
        assert result.header_def is conhead_config.header_defs["header1"]

        process, up_to_date = caplog.record_tuples
        assert process == ("test", logging.INFO, "process src/up-to-date.ext2")
        assert up_to_date == (
            "test",
            logging.INFO,
            "up to date: src/up-to-date.ext2",
        )
