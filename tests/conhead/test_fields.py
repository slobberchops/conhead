# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0
#
# Created: 2022-06-06
# Updated: 2022-06-09
import datetime
import pathlib

import pytest

from conhead import fields
from conhead import util

NOW_DATETIME = datetime.datetime(2019, 12, 10)
NOW_DATE = NOW_DATETIME.date()


@pytest.fixture
def pyproject_path(project_dir) -> pathlib.Path:
    return project_dir / "pyproject.toml"


@pytest.fixture
def pyproject_toml() -> str:
    return "# Py Project"


class TestYears:
    class TestStr:
        @staticmethod
        def test_single_year():
            assert str(fields.Years(2014, 2014)) == "2014"

        @staticmethod
        def test_multi_year():
            assert str(fields.Years(2014, 2015)) == "2014-2015"

    @staticmethod
    def test_iterate_years():
        assert tuple(fields.Years(2014, 2019)) == (2014, 2019)

    class TestParse:
        @staticmethod
        def test_single_year():
            assert fields.Years.parse("2014") == fields.Years(2014, 2014)

        @staticmethod
        def test_multi_year():
            assert fields.Years.parse("2014-2015") == fields.Years(2014, 2015)

        @staticmethod
        @pytest.mark.parametrize(
            "invalid", ["100", "10000", "", "abcd", "2014-100", "2014-10000"]
        )
        def test_invalid(invalid):
            with pytest.raises(ValueError, match=rf"^cannot parse years: {invalid!r}$"):
                fields.Years.parse(invalid)

    @staticmethod
    def test_new(pyproject_path):
        assert fields.Years.new(NOW_DATETIME, pyproject_path) == fields.Years(
            2019, 2019
        )

    @staticmethod
    def test_update(pyproject_path):
        original = fields.Years(2014, 2015)
        assert original.update(NOW_DATETIME, pyproject_path) == fields.Years(2014, 2019)


class TestDateFiel:
    @staticmethod
    def test_str():
        assert str(fields.Date(NOW_DATE)) == "2019-12-10"


class TestDate:
    @staticmethod
    def test_new(pyproject_path):
        assert fields.Date.new(NOW_DATETIME, pyproject_path) == fields.Date(NOW_DATE)

    @staticmethod
    def test_update(pyproject_path):
        original = fields.Date(datetime.date(2012, 6, 12))
        assert original.update(NOW_DATETIME, pyproject_path) == fields.Date(NOW_DATE)


class TestCreated:
    @staticmethod
    def test_new(pyproject_path):
        creation = util.file_creation(pyproject_path).date()
        assert fields.Created.new(NOW_DATETIME, pyproject_path) == fields.Created(
            creation
        )

    @staticmethod
    def test_update(pyproject_path):
        creation = util.file_creation(pyproject_path).date()
        original = fields.Created(datetime.date(2012, 6, 12))
        assert original.update(NOW_DATETIME, pyproject_path) == fields.Created(creation)
