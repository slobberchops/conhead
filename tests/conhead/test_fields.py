# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0

import datetime

import pytest

from conhead import fields


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
    def test_new():
        now = datetime.datetime(2014, 12, 10)
        assert fields.Years.new(now) == fields.Years(2014, 2014)

    @staticmethod
    def test_update():
        now = datetime.datetime(2019, 12, 10)
        original = fields.Years(2014, 2015)
        assert original.update(now) == fields.Years(2014, 2019)
