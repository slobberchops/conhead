# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0
#
import datetime
import re

import pytest

from conhead import fields
from conhead import template

PARSER_TEST_DATA = [
    [template.FieldKind.YEARS, "2014-2018", fields.Years(2014, 2018)],
    [template.FieldKind.DATE, "2012-06-12", fields.Date(datetime.date(2012, 6, 12))],
]


class TestToken:
    @staticmethod
    @pytest.fixture
    def token() -> template.Token:
        return template.Token(
            template.TokenKind.FIELD, "{{YEARS}}", 10, 20, template.FieldKind.YEARS
        )

    @staticmethod
    def test_kind(token):
        assert token.kind == template.TokenKind.FIELD

    @staticmethod
    def test_unparsed(token):
        assert token.unparsed == "{{YEARS}}"

    @staticmethod
    def test_row(token):
        assert token.row == 10

    @staticmethod
    def test_column(token):
        assert token.column == 20

    @staticmethod
    def test_parsed(token):
        assert token.parsed == template.FieldKind.YEARS

    @staticmethod
    def test_repr(token):
        assert repr(token) == "<token:FIELD '{{YEARS}}' 10:20 FieldKind.YEARS>"

    class TestEq:
        @staticmethod
        def test_is(token):
            other = template.Token(
                template.TokenKind.FIELD, "{{YEARS}}", 10, 20, template.FieldKind.YEARS
            )
            assert token == other

        @staticmethod
        @pytest.mark.parametrize(
            "other",
            [
                template.Token(
                    template.TokenKind.ESCAPED,
                    "{{YEARS}}",
                    10,
                    20,
                    template.FieldKind.YEARS,
                ),
                template.Token(
                    template.TokenKind.FIELD,
                    "{{DATE}}",
                    10,
                    20,
                    template.FieldKind.YEARS,
                ),
                template.Token(
                    template.TokenKind.FIELD,
                    "{{YEARS}}",
                    12,
                    20,
                    template.FieldKind.YEARS,
                ),
                template.Token(
                    template.TokenKind.FIELD,
                    "{{YEARS}}",
                    10,
                    22,
                    template.FieldKind.YEARS,
                ),
                template.Token(
                    template.TokenKind.FIELD,
                    "{{YEARS}}",
                    10,
                    20,
                    template.FieldKind.DATE,
                ),
                "not a token",
            ],
        )
        def test_is_not(token, other):
            assert token != other


class TestHeaderParser:
    class TestParseFields:
        @staticmethod
        @pytest.fixture
        def template_field_kind() -> template.FieldKind:
            return template.FieldKind.YEARS

        @staticmethod
        @pytest.fixture
        def template_parser(template_field_kind) -> template.HeaderParser:
            return template.HeaderParser(
                fields=tuple([template_field_kind]),
                regex=re.compile("^test (.*) test"),
            )

        @staticmethod
        def test_non_matching_template(template_parser):
            assert template_parser.parse_fields("has no header") is None

        @staticmethod
        @pytest.mark.parametrize(
            "template_field_kind,unparsed,parsed", PARSER_TEST_DATA
        )
        def test_match_fields(template_parser, unparsed, parsed):
            header = f"test {unparsed} test"
            field_values = template_parser.parse_fields(f"{header}\ncontent")
            (value,) = field_values.fields
            assert value == parsed
            assert field_values.header == header


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
    @pytest.mark.parametrize(
        "field_name,field_kind", [(k.name, k) for k in template.FieldKind]
    )
    def test_field(field_name, field_kind):
        tokens = list(
            template.tokenize_template(
                f"rights reserved\ncopyright {{{{{field_name}}}}}."
            )
        )
        for a, b in zip(
            tokens,
            [
                template.Token(
                    template.TokenKind.CONTENT,
                    "rights reserved",
                    1,
                    1,
                    "rights reserved",
                ),
                template.Token(
                    template.TokenKind.NEWLINE,
                    "\n",
                    1,
                    len("rights reserved") + 1,
                    "\n",
                ),
                template.Token(
                    template.TokenKind.CONTENT, "copyright ", 2, 1, "copyright "
                ),
                template.Token(
                    template.TokenKind.FIELD,
                    f"{{{{{field_name}}}}}",
                    2,
                    len("copyright ") + 1,
                    field_kind,
                ),
                template.Token(
                    template.TokenKind.CONTENT,
                    ".",
                    2,
                    len(f"copyright {{{{{field_name}}}}}") + 1,
                    ".",
                ),
            ],
        ):
            assert a == b
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
                f"{{{{{field_name}}}}}",
                2,
                len("copyright ") + 1,
                field_kind,
            ),
            template.Token(
                template.TokenKind.CONTENT,
                ".",
                2,
                len(f"copyright {{{{{field_name}}}}}") + 1,
                ".",
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
    @pytest.mark.parametrize(
        "template_field_kind,unparsed", [d[:2] for d in PARSER_TEST_DATA]
    )
    def test_fields(template_field_kind, unparsed):
        parser = template.make_template_parser(
            f"line 1 {{{{{template_field_kind.name}}}}}.\n"
        )
        assert parser.fields == (template_field_kind,)

        match = parser.regex.match(f"line 1 {unparsed}.\ncontent")
        assert match
        assert match.group(1) == unparsed

    @staticmethod
    def test_escaping():
        parser = template.make_template_parser("line 1 \\{.\n line 2 \\}. line 3 \\\\.")

        assert parser.fields == ()

        match = parser.regex.match("line 1 {.\n line 2 }. line 3 \\.")
        assert match


@pytest.mark.parametrize("template_field_kind,unparsed,parsed", PARSER_TEST_DATA)
def test_write_header(template_field_kind, unparsed, parsed):
    content = template.write_header(
        f"start {{{{{template_field_kind.name}}}}} end\n",
        (parsed,),
    )

    assert content == f"start {parsed} end\n"
