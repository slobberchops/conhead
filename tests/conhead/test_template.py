import re

import pytest

from conhead import template


class TestTemplateParser:
    class TestParseFields:
        @staticmethod
        @pytest.fixture
        def template_parser() -> template.TemplateParser:
            return template.TemplateParser(
                fields=(template.FieldKind.YEAR, template.FieldKind.YEAR),
                regex=re.compile("^test (.*) test (.*)"),
            )

        @staticmethod
        def test_single_years(template_parser):
            year1, year2 = template_parser.parse_fields("test 2014 test 2015")
            assert year1 == template.Years(2014, 2014)
            assert year2 == template.Years(2015, 2015)

        @staticmethod
        def test_year_range(template_parser):
            year1, year2 = template_parser.parse_fields("test 2014-2016 test 2015-2019")
            assert year1 == template.Years(2014, 2016)
            assert year2 == template.Years(2015, 2019)

        @staticmethod
        def test_matching_header(template_parser):
            ...


class TestTokenizeTemplate:
    @staticmethod
    def test_empty():
        tokens = list(template.tokenize_template(""))
        assert tokens == []

    @staticmethod
    def test_lines():
        tokens = list(template.tokenize_template("\n\n\n"))
        assert tokens == [
            (template.TokenKind.NEWLINE, "\n", 1, 1),
            (template.TokenKind.NEWLINE, "\n", 2, 1),
            (template.TokenKind.NEWLINE, "\n", 3, 1),
        ]

    @staticmethod
    def test_content():
        tokens = list(template.tokenize_template("this is content\n"))
        assert tokens == [
            (template.TokenKind.CONTENT, "this is content", 1, 1),
            (template.TokenKind.NEWLINE, "\n", 1, len("this is content") + 1),
        ]

    @staticmethod
    def test_trailing_content():
        tokens = list(template.tokenize_template("this is content\nand this also"))
        assert tokens == [
            (template.TokenKind.CONTENT, "this is content", 1, 1),
            (template.TokenKind.NEWLINE, "\n", 1, len("this is content") + 1),
            (template.TokenKind.CONTENT, "and this also", 2, 1),
        ]

    @staticmethod
    def test_year():
        tokens = list(
            template.tokenize_template("rights reserved\ncopyright {{YEAR}}.")
        )
        assert tokens == [
            (template.TokenKind.CONTENT, "rights reserved", 1, 1),
            (template.TokenKind.NEWLINE, "\n", 1, len("rights reserved") + 1),
            (template.TokenKind.CONTENT, "copyright ", 2, 1),
            (template.TokenKind.YEAR, "{{YEAR}}", 2, len("copyright ") + 1),
            (template.TokenKind.CONTENT, ".", 2, len("copyright {{YEAR}}") + 1),
        ]

    @staticmethod
    def test_escaped_character():
        tokens = list(template.tokenize_template("\\{\\}\\\\"))
        assert tokens == [
            (template.TokenKind.ESCAPED, "\\{", 1, 1),
            (template.TokenKind.ESCAPED, "\\}", 1, 3),
            (template.TokenKind.ESCAPED, "\\\\", 1, 5),
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
