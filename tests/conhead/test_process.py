# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0
#
import datetime
import logging
import pathlib
import stat
from typing import Iterator

import pytest

from conhead import config
from conhead import fields
from conhead import process as process_module
from conhead import template
from tests.conhead import fixtures

NOW = datetime.datetime(2019, 10, 10)

pyproject_toml = fixtures.populated_pyproject_toml
source_dir = fixtures.populated_source_dir


@pytest.fixture
def logger() -> Iterator[logging.Logger]:
    logger = logging.getLogger("test")
    try:
        logger.setLevel(logging.DEBUG)
        yield logger
    finally:
        del logger.manager.loggerDict["test"]


@pytest.mark.usefixtures("fake_time")
class TestCheckPath:
    @staticmethod
    def test_file_not_found(logger, conhead_config, caplog):
        result = process_module.check_path(
            conhead_config,
            NOW,
            logger,
            "src/unknown.ext1",
            ignore_missing_template=False,
        )
        assert not result.is_up_to_date
        assert result.content is None
        assert result.updated_values is None
        assert result.header_def is conhead_config.header_defs["header1"]

        process, not_found = caplog.record_tuples
        assert process == ("test", logging.DEBUG, "checking: src/unknown.ext1")
        assert not_found == (
            "test",
            logging.ERROR,
            "file not found: src/unknown.ext1",
        )

    @staticmethod
    def test_not_readable(logger, conhead_config, caplog):
        result = process_module.check_path(
            conhead_config,
            NOW,
            logger,
            "src/unreadable.ext1",
            ignore_missing_template=False,
        )
        assert not result.is_up_to_date
        assert result.content is None
        assert result.updated_values is None
        assert result.header_def is conhead_config.header_defs["header1"]

        process, not_found = caplog.record_tuples
        assert process == ("test", logging.DEBUG, "checking: src/unreadable.ext1")
        assert not_found == (
            "test",
            logging.ERROR,
            "unreadable: src/unreadable.ext1",
        )

    @staticmethod
    def test_oserror(logger, conhead_config, caplog, monkeypatch):
        def fake_open(*args, **kwargs):
            raise TimeoutError("timeout error")

        monkeypatch.setattr(pathlib.Path, "open", fake_open)

        result = process_module.check_path(
            conhead_config,
            NOW,
            logger,
            "src/unknown.ext1",
            ignore_missing_template=False,
        )
        assert not result.is_up_to_date
        assert result.content is None
        assert result.updated_values is None
        assert result.header_def is conhead_config.header_defs["header1"]

        process, not_found = caplog.record_tuples
        assert process == ("test", logging.DEBUG, "checking: src/unknown.ext1")
        assert not_found == (
            "test",
            logging.ERROR,
            "timeout error (TimeoutError): src/unknown.ext1",
        )

    @staticmethod
    def test_unmatched(conhead_config, logger, source_dir, caplog):
        result = process_module.check_path(
            conhead_config,
            NOW,
            logger,
            "src/unmatched.unknown",
            ignore_missing_template=False,
        )
        assert not result.is_up_to_date
        assert result.content is None
        assert result.updated_values is None
        assert result.header_def is None

        process, not_found = caplog.record_tuples
        assert process == ("test", logging.DEBUG, "checking: src/unmatched.unknown")
        assert not_found == (
            "test",
            logging.ERROR,
            "no header def: src/unmatched.unknown",
        )

    @staticmethod
    def test_unmatched_ignore(conhead_config, logger, source_dir, caplog):
        result = process_module.check_path(
            conhead_config,
            NOW,
            logger,
            "src/unmatched.unknown",
            ignore_missing_template=True,
        )
        assert not result.is_up_to_date
        assert result.content is None
        assert result.updated_values is None
        assert result.header_def is None

        (skip,) = caplog.record_tuples
        assert skip == ("test", logging.DEBUG, "skipping: src/unmatched.unknown")

    @staticmethod
    def test_empty(conhead_config, logger, source_dir, caplog):
        result = process_module.check_path(
            conhead_config, NOW, logger, "src/empty.ext1", ignore_missing_template=False
        )
        assert not result.is_up_to_date
        assert result.content == source_dir["empty.ext1"]
        assert result.updated_values is None
        assert result.header_def is conhead_config.header_defs["header1"]

        process, not_found = caplog.record_tuples
        assert process == ("test", logging.DEBUG, "checking: src/empty.ext1")
        assert not_found == (
            "test",
            logging.WARNING,
            "missing header: src/empty.ext1",
        )

    @staticmethod
    def test_no_header(conhead_config, logger, source_dir, caplog):
        result = process_module.check_path(
            conhead_config,
            NOW,
            logger,
            "src/no-header.ext3",
            ignore_missing_template=False,
        )
        assert not result.is_up_to_date
        assert result.content == config.deindent_string(source_dir["no-header.ext3"])
        assert result.updated_values is None
        assert result.header_def is conhead_config.header_defs["header2"]

        process, not_found = caplog.record_tuples
        assert process == ("test", logging.DEBUG, "checking: src/no-header.ext3")
        assert not_found == (
            "test",
            logging.WARNING,
            "missing header: src/no-header.ext3",
        )

    @staticmethod
    def test_out_of_date(conhead_config, logger, source_dir, caplog):
        result = process_module.check_path(
            conhead_config,
            NOW,
            logger,
            "src/out-of-date.ext4",
            ignore_missing_template=False,
        )
        assert not result.is_up_to_date
        assert result.content == config.deindent_string(source_dir["out-of-date.ext4"])
        assert result.updated_values
        years1, years2 = result.updated_values
        assert years1 == fields.Years(2018, 2019)
        assert years2 == fields.Years(2014, 2019)
        assert result.header_def is conhead_config.header_defs["header2"]

        process, not_found = caplog.record_tuples
        assert process == ("test", logging.DEBUG, "checking: src/out-of-date.ext4")
        assert not_found == (
            "test",
            logging.WARNING,
            "out of date: src/out-of-date.ext4",
        )

    @staticmethod
    def test_up_to_date(conhead_config, logger, source_dir, caplog):
        result = process_module.check_path(
            conhead_config,
            NOW,
            logger,
            "src/up-to-date.ext2",
            ignore_missing_template=False,
        )
        assert result.is_up_to_date
        assert result.content == config.deindent_string(source_dir["up-to-date.ext2"])
        assert result.updated_values is None
        assert result.header_def is conhead_config.header_defs["header1"]

        process, up_to_date = caplog.record_tuples
        assert process == ("test", logging.DEBUG, "checking: src/up-to-date.ext2")
        assert up_to_date == (
            "test",
            logging.INFO,
            "up to date: src/up-to-date.ext2",
        )


class TestRewriteFile:
    @staticmethod
    def test_unwritable(conhead_config, logger, caplog):
        header_def = conhead_config.header_defs["header1"]
        field_values = (fields.Years(2019, 2019), fields.Years(2014, 2019))

        path = pathlib.Path("result.ext1")
        path.write_text("")
        path.chmod(stat.S_IREAD)

        assert not process_module.rewrite_file(
            "result.ext1",
            logger,
            "end of file\n",
            header_def,
            field_values,
            None,
            False,
            False,
        )

        empty = pathlib.Path("result.ext1").read_text()
        assert empty == ""

        process, error = caplog.record_tuples
        assert process == ("test", logging.INFO, "rewriting: result.ext1")
        assert error == ("test", logging.ERROR, "unwritable: result.ext1")

    @staticmethod
    def test_oserror(conhead_config, logger, caplog, monkeypatch):
        header_def = conhead_config.header_defs["header1"]
        field_values = (fields.Years(2019, 2019), fields.Years(2014, 2019))

        def fake_open(*args, **kwargs):
            raise TimeoutError("timeout error")

        monkeypatch.setattr(pathlib.Path, "open", fake_open)

        assert not process_module.rewrite_file(
            "result.ext1",
            logger,
            "end of file\n",
            header_def,
            field_values,
            None,
            False,
            False,
        )

        process, error = caplog.record_tuples
        assert process == ("test", logging.INFO, "rewriting: result.ext1")
        assert error == (
            "test",
            logging.ERROR,
            "timeout error (TimeoutError): result.ext1",
        )

    @staticmethod
    def test_all_new(conhead_config, logger, caplog):
        header_def = conhead_config.header_defs["header1"]
        field_values = (fields.Years(2019, 2019), fields.Years(2014, 2019))
        assert process_module.rewrite_file(
            "result.ext1",
            logger,
            "end of file\n",
            header_def,
            field_values,
            None,
            False,
            False,
        )

        with_header = pathlib.Path("result.ext1").read_text()
        assert with_header == "# line 1 2019\n# line 2 2014-2019\nend of file\n"

        (process,) = caplog.record_tuples
        assert process == ("test", logging.INFO, "rewriting: result.ext1")

    @staticmethod
    def test_update_existing(conhead_config, logger, caplog):
        header_def = conhead_config.header_defs["header1"]
        field_values = (fields.Years(2019, 2019), fields.Years(2014, 2019))
        existing_header = "# line 1 2011\n# line 2 2011-2014\n"
        existing_content = f"{existing_header}end of file\n"
        parsed_values = template.ParsedValues(field_values, existing_header)
        assert process_module.rewrite_file(
            pathlib.Path("result.ext1"),
            logger,
            existing_content,
            header_def,
            field_values,
            parsed_values,
            False,
            False,
        )

        with_header = pathlib.Path("result.ext1").read_text()
        assert with_header == "# line 1 2019\n# line 2 2014-2019\nend of file\n"

        (process,) = caplog.record_tuples
        assert process == ("test", logging.INFO, "rewriting: result.ext1")

    @staticmethod
    def test_remove_header_has_header(conhead_config, logger, caplog):
        header_def = conhead_config.header_defs["header1"]
        field_values = (fields.Years(2019, 2019), fields.Years(2014, 2019))
        existing_header = "# line 1 2011\n# line 2 2011-2014\n"
        existing_content = f"{existing_header}end of file\n"
        parsed_values = template.ParsedValues(field_values, existing_header)
        assert process_module.rewrite_file(
            pathlib.Path("result.ext1"),
            logger,
            existing_content,
            header_def,
            field_values,
            parsed_values,
            True,
            False,
        )

        with_header = pathlib.Path("result.ext1").read_text()
        assert with_header == "end of file\n"

        (process,) = caplog.record_tuples
        assert process == ("test", logging.INFO, "removing header: result.ext1")

    class TestShowChanges:
        @staticmethod
        def test_new_header(conhead_config, logger, caplog, capsys):
            header_def = conhead_config.header_defs["header1"]
            field_values = (fields.Years(2019, 2019), fields.Years(2014, 2019))
            assert process_module.rewrite_file(
                "result.ext1",
                logger,
                "end of file\n",
                header_def,
                field_values,
                None,
                False,
                True,
            )

            with_header = pathlib.Path("result.ext1").read_text()
            assert with_header == "# line 1 2019\n# line 2 2014-2019\nend of file\n"

            (process,) = caplog.record_tuples
            assert process == ("test", logging.INFO, "rewriting: result.ext1")

            out, _ = capsys.readouterr()

            assert out == "\n".join(
                [
                    "result.ext1",
                    "New header",
                    "",
                    "# line 1 2019",
                    "# line 2 2014-2019",
                    "",
                    "",
                    "",
                ]
            )

        @staticmethod
        def test_update_existing(conhead_config, logger, caplog, capsys):
            header_def = conhead_config.header_defs["header1"]
            field_values = (fields.Years(2019, 2019), fields.Years(2014, 2019))
            existing_header = "# line 1 2011\n# line 2 2011-2014\n"
            existing_content = f"{existing_header}end of file\n"
            parsed_values = template.ParsedValues(field_values, existing_header)
            assert process_module.rewrite_file(
                pathlib.Path("result.ext1"),
                logger,
                existing_content,
                header_def,
                field_values,
                parsed_values,
                False,
                True,
            )

            with_header = pathlib.Path("result.ext1").read_text()
            assert with_header == "# line 1 2019\n# line 2 2014-2019\nend of file\n"

            (process,) = caplog.record_tuples
            assert process == ("test", logging.INFO, "rewriting: result.ext1")

            out, _ = capsys.readouterr()
            assert out == "\n".join(
                [
                    "result.ext1",
                    "# line 1 2011",
                    "# line 2 2011-2014",
                    "",
                    "",
                    "# line 1 2019",
                    "# line 2 2014-2019",
                    "",
                    "",
                    "",
                ]
            )

        @staticmethod
        def test_remove_header(conhead_config, logger, caplog, capsys):
            header_def = conhead_config.header_defs["header1"]
            field_values = (fields.Years(2019, 2019), fields.Years(2014, 2019))
            existing_header = "# line 1 2011\n# line 2 2011-2014\n"
            existing_content = f"{existing_header}end of file\n"
            parsed_values = template.ParsedValues(field_values, existing_header)
            assert process_module.rewrite_file(
                pathlib.Path("result.ext1"),
                logger,
                existing_content,
                header_def,
                field_values,
                parsed_values,
                True,
                True,
            )

            with_header = pathlib.Path("result.ext1").read_text()
            assert with_header == "end of file\n"

            (process,) = caplog.record_tuples
            assert process == ("test", logging.INFO, "removing header: result.ext1")

            out, _ = capsys.readouterr()
            assert out == "\n".join(
                [
                    "result.ext1",
                    "# line 1 2011",
                    "# line 2 2011-2014",
                    "",
                    "",
                    "Header removed",
                    "",
                    "",
                ]
            )
