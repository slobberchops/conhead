# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0

import io
import re

import pytest

from conhead import fields
from conhead import template


class TestHeaderParser:
    class TestParseFields:
        @staticmethod
        @pytest.fixture
        def template_parser() -> template.HeaderParser:
            return template.HeaderParser(
                fields=(template.FieldKind.YEAR, template.FieldKind.YEAR),
                regex=re.compile("^test (.*) test (.*)"),
            )

        @staticmethod
        def test_non_matching_template(template_parser):
            assert template_parser.parse_fields("has no header") is None

        @staticmethod
        def test_single_years(template_parser):
            values = template_parser.parse_fields("test 2014 test 2015\ncontent")
            year1, year2 = values.fields
            assert year1 == fields.Years(2014, 2014)
            assert year2 == fields.Years(2015, 2015)
            assert values.header == "test 2014 test 2015"

        @staticmethod
        def test_year_range(template_parser):
            values = template_parser.parse_fields(
                "test 2014-2016 test 2015-2019\n content"
            )
            year1, year2 = values.fields
            assert year1 == fields.Years(2014, 2016)
            assert year2 == fields.Years(2015, 2019)
            assert values.header == "test 2014-2016 test 2015-2019"


class TestTokenizeTemplate:
    @staticmethod
    def test_empty():
        tokens = list(template.tokenize_template(""))
        assert tokens == []

    @staticmethod
    def test_lines():
        tokens = list(template.tokenize_template("\n\n\n"))
        assert tokens == [
            template.Token(template.TokenKind.NEWLINE, "\n", 1, 1, "\n"),
            template.Token(template.TokenKind.NEWLINE, "\n", 2, 1, "\n"),
            template.Token(template.TokenKind.NEWLINE, "\n", 3, 1, "\n"),
        ]

    @staticmethod
    def test_content():
        tokens = list(template.tokenize_template("this is content\n"))
        assert tokens == [
            template.Token(
                template.TokenKind.CONTENT, "this is content", 1, 1, "this is content"
            ),
            template.Token(
                template.TokenKind.NEWLINE, "\n", 1, len("this is content") + 1, "\n"
            ),
        ]

    @staticmethod
    def test_trailing_content():
        tokens = list(template.tokenize_template("this is content\nand this also"))
        assert tokens == [
            template.Token(
                template.TokenKind.CONTENT, "this is content", 1, 1, "this is content"
            ),
            template.Token(
                template.TokenKind.NEWLINE, "\n", 1, len("this is content") + 1, "\n"
            ),
            template.Token(
                template.TokenKind.CONTENT, "and this also", 2, 1, "and this also"
            ),
        ]

    @staticmethod
    def test_field():
        tokens = list(
            template.tokenize_template("rights reserved\ncopyright {{YEAR}}.")
        )
        assert tokens == [
            template.Token(
                template.TokenKind.CONTENT, "rights reserved", 1, 1, "rights reserved"
            ),
            template.Token(
                template.TokenKind.NEWLINE, "\n", 1, len("rights reserved") + 1, "\n"
            ),
            template.Token(
                template.TokenKind.CONTENT, "copyright ", 2, 1, "copyright "
            ),
            template.Token(
                template.TokenKind.FIELD,
                "{{YEAR}}",
                2,
                len("copyright ") + 1,
                template.FieldKind.YEAR,
            ),
            template.Token(
                template.TokenKind.CONTENT, ".", 2, len("copyright {{YEAR}}") + 1, "."
            ),
        ]

    @staticmethod
    def test_unknown_field():
        with pytest.raises(
            template.TemplateError, match="^Unknown field type 'unknown' at 2:11$"
        ):
            list(template.tokenize_template("rights reserved\ncopyright {{unknown}}."))

    @staticmethod
    def test_escaped_character():
        tokens = list(template.tokenize_template("\\{\\}\\\\"))
        assert tokens == [
            template.Token(template.TokenKind.ESCAPED, "\\{", 1, 1, "{"),
            template.Token(template.TokenKind.ESCAPED, "\\}", 1, 3, "}"),
            template.Token(template.TokenKind.ESCAPED, "\\\\", 1, 5, "\\"),
        ]

    @staticmethod
    @pytest.mark.parametrize("chr", ["{", "}", "\\"])
    def test_invalid(chr):
        re_chr = re.escape(repr(chr))
        with pytest.raises(
            template.TemplateError, match=rf"^Invalid character {re_chr} found at 1:13"
        ):
            list(template.tokenize_template(f"has invalid {chr}."))


class TestMakeTemplateRe:
    @staticmethod
    def test_empty():
        parser = template.make_template_parser("")
        assert parser.fields == ()
        assert parser.regex.pattern == "^"

    @staticmethod
    def test_static_content():
        parser = template.make_template_parser("template line 1\ntemplate line 2")
        assert parser.fields == ()
        assert parser.regex.pattern == "^" + re.escape(
            "template line 1\ntemplate line 2"
        )

    @staticmethod
    def test_years():
        parser = template.make_template_parser("line 1 {{YEAR}}.\nline 2 {{YEAR}}.")
        assert parser.fields == (
            template.FieldKind.YEAR,
            template.FieldKind.YEAR,
        )

        match = parser.regex.match("line 1 2014.\nline 2 2014-2018.")
        assert match
        assert match.group(1) == "2014"
        assert match.group(2) == "2014-2018"

    @staticmethod
    def test_escaping():
        parser = template.make_template_parser("line 1 \\{.\n line 2 \\}. line 3 \\\\.")

        assert parser.fields == ()

        match = parser.regex.match("line 1 {.\n line 2 }. line 3 \\.")
        assert match


def test_write_header():
    content = io.StringIO()
    template.write_header(
        "start {{YEAR}} middle\n{{YEAR}} \\{end\\}",
        (fields.Years(2019, 2019), fields.Years(2014, 2019)),
        content,
    )

    assert content.getvalue() == "start 2019 middle\n2014-2019 {end}"
