# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0
#
import copy

import pytest

from conhead import util


class TestFrozenDict:
    class TestConstructor:
        @staticmethod
        def test_empty():
            assert dict(util.FrozenDict()) == {}

        @staticmethod
        def test_kwargs():
            assert dict(util.FrozenDict(a=1, b=2)) == {"a": 1, "b": 2}

        @staticmethod
        def test_copy():
            dct = {"a": 1, "b": 2}
            assert dict(util.FrozenDict(dct)) == dct

    class TestWithDct:
        @staticmethod
        @pytest.fixture
        def dct():
            return util.FrozenDict(a=1, b=2, c=util.FrozenDict())

        @staticmethod
        def test_len(dct):
            assert len(util.FrozenDict()) == 0
            assert len(dct) == 3

        @staticmethod
        def test_get_item(dct):
            assert dct["a"] == 1
            assert dct["b"] == 2
            assert dct["c"] == {}

        @staticmethod
        def test_iter(dct):
            i = iter(dct)
            assert next(i) == "a"
            assert next(i) == "b"
            assert next(i) == "c"
            with pytest.raises(StopIteration):
                next(i)

        @staticmethod
        def test_contains(dct):
            assert "a" in dct
            assert "b" in dct
            assert "c" in dct

        @staticmethod
        def test_not_contains(dct):
            assert "d" not in dct
            assert "e" not in dct
            assert "f" not in dct

        @staticmethod
        def test_repr(dct):
            assert repr(dct) == "{'a': 1, 'b': 2, 'c': {}}"

        class TestOr:
            @staticmethod
            def test_compatible(dct):
                new_dct = dct | dict(c=5, d=6, e=7)
                assert dict(new_dct) == {"a": 1, "b": 2, "c": 5, "d": 6, "e": 7}

            @staticmethod
            def test_incompatble(dct):
                with pytest.raises(TypeError):
                    dct | "a string"  # type: ignore

        class TestRor:
            @staticmethod
            def test_compatible(dct):
                new_dct = dict(c=5, d=6, e=7) | dct
                assert dict(new_dct) == {"a": 1, "b": 2, "c": {}, "d": 6, "e": 7}

            @staticmethod
            def test_incompatble(dct):
                with pytest.raises(TypeError):
                    "a string" | dct  # type: ignore

        @staticmethod
        def test_copy_operator(dct):
            cp = copy.copy(dct)
            assert isinstance(cp, util.FrozenDict)
            assert cp == dct
            assert cp is not dct
            assert cp["c"] is dct["c"]

        @staticmethod
        def test_copy(dct):
            cp = dct.copy()
            assert isinstance(cp, util.FrozenDict)
            assert cp == dct
            assert cp is not dct
            assert cp["c"] is dct["c"]

        @staticmethod
        def test_hash(dct):
            h = hash(dct)
            assert isinstance(h, int)
            assert h == hash((("a", 1), ("b", 2), ("c", util.FrozenDict())))
