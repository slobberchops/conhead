# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0
#
# Created: 2022-06-06
# Updated: 2022-06-09
import datetime
import inspect
import logging
import pathlib
import sys

import click
import pytest

from conhead import main
from tests.conhead import file_testing
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


class TestIterFilesystem:
    @staticmethod
    @pytest.fixture
    def project_dir_content() -> file_testing.DirContent:
        return {
            "a-file": "",
            "a-dir": {
                "a-sub-file1": "",
                "a-sub-file2": "",
                "another-dir": {
                    "a-sub-file3": "",
                },
            },
            "sym-to-file": file_testing.Symlink("a-file"),
            "sym-to-dir": file_testing.Symlink("a-dir"),
        }

    @staticmethod
    def test_iter_dir(project_dir):
        iterator = main.iter_dir(project_dir)
        assert inspect.isgenerator(iterator)

        a_file, sub_file3, sub_file2, sub_file1 = list(iterator)
        assert a_file.relative_to(project_dir) == pathlib.Path("a-file")
        assert sub_file1.relative_to(project_dir) == pathlib.Path("a-dir/a-sub-file1")
        assert sub_file2.relative_to(project_dir) == pathlib.Path("a-dir/a-sub-file2")
        assert sub_file3.relative_to(project_dir) == pathlib.Path(
            "a-dir/another-dir/a-sub-file3"
        )

    @staticmethod
    @pytest.mark.skipif(sys.platform.startswith("win"), reason="Do not run on Windows")
    @pytest.mark.parametrize("project_dir_content", [{"a-pipe": file_testing.Fifo()}])
    def test_iter_non_file(project_dir):
        iterator = main.iter_dir(project_dir)
        assert inspect.isgenerator(iterator)
        assert list(iterator) == []

    class TestIterPath:
        @staticmethod
        def test_file(project_dir):
            iterator = main.iter_path(project_dir / "a-file")
            assert inspect.isgenerator(iterator)

            ((a_file, is_param),) = iterator
            assert a_file == project_dir / "a-file"
            assert is_param

        @staticmethod
        def test_does_not_exist(project_dir):
            iterator = main.iter_path(project_dir / "not-real")
            assert inspect.isgenerator(iterator)

            ((not_real, is_param),) = iterator
            assert not_real == project_dir / "not-real"
            assert is_param

        @staticmethod
        def test_dir(project_dir):
            iterator = main.iter_path(project_dir / "a-dir")
            assert inspect.isgenerator(iterator)

            (
                (sub_file3, is_param1),
                (sub_file2, is_param2),
                (sub_file1, is_param3),
            ) = iterator
            assert sub_file1 == project_dir / "a-dir" / "a-sub-file1"
            assert not is_param1
            assert sub_file2 == project_dir / "a-dir" / "a-sub-file2"
            assert not is_param2
            assert sub_file3 == project_dir / "a-dir" / "another-dir" / "a-sub-file3"
            assert not is_param3


@pytest.mark.usefixtures("fake_time")
class TestMain:
    source_dir = staticmethod(fixtures.populated_source_dir)
    pyproject_toml = staticmethod(fixtures.populated_pyproject_toml)

    @staticmethod
    def test_check_and_delete_mutually_exclusive(cli_runner):
        result = cli_runner.invoke(main.main, ["--check", "--delete"])
        assert result.exit_code == click.BadOptionUsage.exit_code
        assert "Error: --check and --delete are mutually exclusive" in result.stdout

    @staticmethod
    @pytest.mark.parametrize("pyproject_toml", [None])
    def test_no_config(cli_runner, caplog):
        result = cli_runner.invoke(main.main, [])
        assert result.exit_code == 1

        (record,) = caplog.record_tuples
        assert record == (
            "conhead",
            logging.ERROR,
            "pyproject.toml not found",
        )

    @staticmethod
    @pytest.mark.parametrize("pyproject_toml", [""])
    def test_no_header_defs(cli_runner, caplog):
        result = cli_runner.invoke(main.main, [])
        assert result.exit_code == 1

        (record,) = caplog.record_tuples
        assert record == (
            "conhead",
            logging.ERROR,
            "no header configuration defined",
        )

    class TestCustomConfig:
        @staticmethod
        @pytest.fixture
        def pyproject_toml():
            return None

        conhead_toml = staticmethod(fixtures.populated_pyproject_toml)

        @staticmethod
        @pytest.fixture
        def project_dir_content(project_dir_content, conhead_toml):
            project_dir_content["conhead.toml"] = conhead_toml
            return project_dir_content

        @staticmethod
        @pytest.mark.parametrize("conhead_toml", [None])
        def test_config_error(cli_runner, caplog):
            result = cli_runner.invoke(
                main.main, ["--config", "conhead.toml", "src/up-to-date.ext2"]
            )
            assert result.exit_code == 1

            assert caplog.record_tuples == [
                (
                    "conhead",
                    logging.ERROR,
                    (
                        "Unable read configuration: [Errno 2] "
                        "No such file or directory: 'conhead.toml'"
                    ),
                )
            ]

        @staticmethod
        def test_success(cli_runner, caplog):
            result = cli_runner.invoke(
                main.main, ["--config", "conhead.toml", "src/up-to-date.ext2"]
            )
            assert result.exit_code == 0

            assert caplog.record_tuples == []

    @staticmethod
    def test_no_errors(cli_runner, caplog):
        result = cli_runner.invoke(main.main, ["-vvv", "src/up-to-date.ext2"])
        assert result.exit_code == 0

        process, up_to_date = caplog.record_tuples
        assert process == ("conhead", logging.DEBUG, "checking: src/up-to-date.ext2")
        assert up_to_date == (
            "conhead",
            logging.INFO,
            "up to date: src/up-to-date.ext2",
        )

    @staticmethod
    def test_no_header_def(cli_runner, caplog):
        result = cli_runner.invoke(main.main, ["-vvv", "src/unmatched.unknown"])
        assert result.exit_code == 1

        process, no_header_def = caplog.record_tuples
        assert process == ("conhead", logging.DEBUG, "checking: src/unmatched.unknown")
        assert no_header_def == (
            "conhead",
            logging.ERROR,
            "no header def: src/unmatched.unknown",
        )

    @staticmethod
    def test_has_errors_check(cli_runner, caplog):
        result = cli_runner.invoke(
            main.main,
            ["--check", "-vvv", "src/up-to-date.ext2", "src/out-of-date.ext4"],
        )
        assert result.exit_code == 1

        process1, ok, process2, error = caplog.record_tuples
        assert process1 == ("conhead", logging.DEBUG, "checking: src/up-to-date.ext2")
        assert ok == (
            "conhead",
            logging.INFO,
            "up to date: src/up-to-date.ext2",
        )
        assert process2 == ("conhead", logging.DEBUG, "checking: src/out-of-date.ext4")
        assert error == (
            "conhead",
            logging.WARNING,
            "out of date: src/out-of-date.ext4",
        )

    @staticmethod
    def test_no_header(cli_runner, caplog):
        result = cli_runner.invoke(
            main.main,
            ["-vvv", "src/no-header.ext3"],
        )
        assert result.exit_code == 1

        rewritten = pathlib.Path("src/no-header.ext3").read_text()
        assert rewritten == "// line 1 2019\n// line 2 2019\n// No proper header\n"

        load, error, write = caplog.record_tuples
        assert load == ("conhead", logging.DEBUG, "checking: src/no-header.ext3")
        assert error == (
            "conhead",
            logging.WARNING,
            "missing header: src/no-header.ext3",
        )
        assert write == ("conhead", logging.INFO, "rewriting: src/no-header.ext3")

    @staticmethod
    def test_out_of_date(cli_runner, caplog):
        result = cli_runner.invoke(
            main.main,
            ["-vvv", "src/out-of-date.ext4"],
        )
        assert result.exit_code == 1

        rewritten = pathlib.Path("src/out-of-date.ext4").read_text()
        assert rewritten == "// line 1 2018-2019\n// line 2 2014-2019\ncontent\n"

        load, error, write = caplog.record_tuples
        assert load == ("conhead", logging.DEBUG, "checking: src/out-of-date.ext4")
        assert error == (
            "conhead",
            logging.WARNING,
            "out of date: src/out-of-date.ext4",
        )
        assert write == ("conhead", logging.INFO, "rewriting: src/out-of-date.ext4")

    @staticmethod
    def test_quiet(cli_runner, caplog):
        result = cli_runner.invoke(
            main.main,
            ["--check", "-qqq", "src/up-to-date.ext2", "src/out-of-date.ext4"],
        )
        assert result.exit_code == 1

        assert not caplog.record_tuples

    @staticmethod
    def test_iterate_dir(cli_runner, caplog, project_dir):
        result = cli_runner.invoke(
            main.main,
            [
                "-vvv",
                "src/sub-dir",
            ],
        )
        assert result.exit_code == 1
        (
            process1,
            up_to_date1,
            skip,
            process2,
            up_to_date2,
            process3,
            missing,
            write,
        ) = caplog.record_tuples

        assert process1 == (
            "conhead",
            logging.DEBUG,
            "checking: src/sub-dir/file1.ext1",
        )
        assert up_to_date1 == (
            "conhead",
            logging.INFO,
            "up to date: src/sub-dir/file1.ext1",
        )
        assert skip == ("conhead", logging.DEBUG, "skipping: src/sub-dir/file3.unknown")
        assert process2 == (
            "conhead",
            logging.DEBUG,
            "checking: src/sub-dir/file2.ext3",
        )

        assert process3 == (
            "conhead",
            logging.DEBUG,
            "checking: src/sub-dir/file4.ext1",
        )

        assert missing == (
            "conhead",
            logging.WARNING,
            "missing header: src/sub-dir/file4.ext1",
        )

        assert write == (
            "conhead",
            logging.INFO,
            "rewriting: src/sub-dir/file4.ext1",
        )

    @staticmethod
    def test_delete(cli_runner, caplog):
        result = cli_runner.invoke(
            main.main,
            [
                "-vvv",
                "--delete",
                "src/no-header.ext3",
                "src/up-to-date.ext2",
                "src/out-of-date.ext4",
            ],
        )
        assert result.exit_code == 1

        rewritten = pathlib.Path("src/no-header.ext3").read_text()
        assert rewritten == "// No proper header\n"

        rewritten = pathlib.Path("src/up-to-date.ext2").read_text()
        assert rewritten == ""

        rewritten = pathlib.Path("src/out-of-date.ext4").read_text()
        assert rewritten == "content\n"

        (
            process1,
            missing_header,
            process2,
            up_to_date,
            remove1,
            process3,
            out_of_date,
            remove3,
        ) = caplog.record_tuples

        assert process1 == ("conhead", logging.DEBUG, "checking: src/no-header.ext3")

        assert missing_header == (
            "conhead",
            logging.WARNING,
            "missing header: src/no-header.ext3",
        )

        assert process2 == ("conhead", logging.DEBUG, "checking: src/up-to-date.ext2")

        assert up_to_date == (
            "conhead",
            logging.INFO,
            "up to date: src/up-to-date.ext2",
        )

        assert remove1 == (
            "conhead",
            logging.INFO,
            "removing header: src/up-to-date.ext2",
        )

        assert process3 == ("conhead", logging.DEBUG, "checking: src/out-of-date.ext4")

        assert out_of_date == (
            "conhead",
            logging.WARNING,
            "out of date: src/out-of-date.ext4",
        )

        assert remove3 == (
            "conhead",
            logging.INFO,
            "removing header: src/out-of-date.ext4",
        )

    @staticmethod
    def test_process_whole_dir(cli_runner, caplog, project_dir):
        result = cli_runner.invoke(main.main, ["-vvv"])
        assert result.exit_code == 1
        update_reports = [
            message
            for (_, _, message) in caplog.record_tuples
            if message.startswith("checking:") or message.startswith("skipping:")
        ]

        assert update_reports == [
            "skipping: pyproject.toml",
            "checking: src/up-to-date.ext2",
            "checking: src/no-header.ext3",
            "checking: src/out-of-date.ext4",
            "checking: src/sub-dir/file1.ext1",
            "skipping: src/sub-dir/file3.unknown",
            "checking: src/sub-dir/file2.ext3",
            "checking: src/sub-dir/file4.ext1",
            "checking: src/unreadable.ext1",
            "checking: src/empty.ext1",
            "skipping: src/unmatched.unknown",
        ]
