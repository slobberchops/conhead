import re

import pytest

from conhead import template


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
        groups, template_re = template.make_template_re("")
        assert groups == {}
        assert template_re.pattern == "^"

    @staticmethod
    def test_static_content():
        groups, template_re = template.make_template_re(
            "template line 1\ntemplate line 2"
        )
        assert groups == {}
        assert template_re.pattern == "^" + re.escape(
            "template line 1\ntemplate line 2"
        )

    @staticmethod
    def test_years():
        groups, template_re = template.make_template_re(
            "line 1 {{YEAR}}.\nline 2 {{YEAR}}."
        )
        assert groups == {
            "grp0": template.MarkKind.YEAR,
            "grp1": template.MarkKind.YEAR,
        }

        match = template_re.match("line 1 2014.\nline 2 2014-2018.")
        assert match
        assert match.group("grp0") == "2014"
        assert match.group("grp1") == "2014-2018"

    @staticmethod
    def test_escaping():
        groups, template_re = template.make_template_re(
            "line 1 \\{.\n line 2 \\}. line 3 \\\\."
        )

        assert groups == {}

        match = template_re.match("line 1 {.\n line 2 }. line 3 \\.")
        assert match
