import os

import pytest

from conhead import config
from conhead import template
from conhead import util
from tests.conhead import file_testing


class TestDeindentString:
    @staticmethod
    def test_empty_string():
        assert config.deindent_string("") == ""

    @staticmethod
    def test_indents():
        string = """
            {
                {
                    {
                    }
                }
            }
        """
        assert config.deindent_string(string) == (
            "\n" "{\n" "    {\n" "        {\n" "        }\n" "    }\n" "}\n"
        )


class TestHeader:
    @staticmethod
    def test_extensions_re():
        cfg = config.Header(name="test", template="", extensions=("ext1", "ext2"))
        regex = cfg.extensions_re
        assert regex.pattern == r"\.(?:ext1|ext2)$"
        assert regex.search("path1/path2/file.ext1")
        assert regex.search("path1/path2/file.ext2")

    @staticmethod
    def test_template_re():
        cfg = config.Header(
            name="test", template="test {{YEAR}} test", extensions=("ext1", "ext2")
        )
        assert cfg.template_re.pattern == "^test\\ (?P<grp0>\\d{4}(?:-\\d{4})?)\\ test"

        match = cfg.template_re.match("test 2014-2018 test\nrest of doc")
        assert match
        assert match.lastgroup == "grp0"

    @staticmethod
    def test_mark_map():
        cfg = config.Header(
            name="test",
            template="test {{YEAR}} test {{YEAR}}",
            extensions=("ext1", "ext2"),
        )
        assert cfg.mark_map == util.FrozenDict(
            {
                "grp0": template.MarkKind.YEAR,
                "grp1": template.MarkKind.YEAR,
            }
        )

    class TestFromDict:
        @staticmethod
        @pytest.mark.parametrize(
            "pyproject_toml",
            [
                """
                [tool.conhead.header.py]
                """
            ],
        )
        def test_missing_template():
            with pytest.raises(
                config.ConfigError,
                match=r"^tool.conhead.header.py: template is required$",
            ):
                config.load()

        @staticmethod
        @pytest.mark.parametrize(
            "pyproject_toml",
            [
                """
                [tool.conhead.header.py]
                template = 20
                """
            ],
        )
        def test_template_not_string():
            with pytest.raises(
                config.ConfigError,
                match=r"^tool.conhead.header.py: template must be str$",
            ):
                config.load()

        @staticmethod
        @pytest.mark.parametrize(
            "pyproject_toml",
            [
                """
                [tool.conhead.header.py]
                template = ""
                extensions = "extensions"
                """
            ],
        )
        def test_extensions_not_list():
            with pytest.raises(
                config.ConfigError,
                match=r"^tool.conhead.header.py: extensions must be list of strings$",
            ):
                config.load()

        @staticmethod
        @pytest.mark.parametrize(
            "pyproject_toml",
            [
                """
                [tool.conhead.header.py]
                template = ""
                extensions = ["ex1", 20]
                """
            ],
        )
        def test_extensions_not_list_of_strings():
            with pytest.raises(
                config.ConfigError,
                match=r"^tool.conhead.header.py: extensions must be list of strings$",
            ):
                config.load()

        @staticmethod
        @pytest.mark.parametrize(
            "pyproject_toml",
            [
                """
                [tool.conhead.header.py]
                template = ""
                unexpected1 = "unexpected1"
                unexpected3 = "unexpected3"
                unexpected2 = "unexpected2"
                """
            ],
        )
        def test_unexpected_options():
            with pytest.raises(
                config.ConfigError,
                match=r"^unexpected options: unexpected1, unexpected2, unexpected3$",
            ):
                config.load()

        @staticmethod
        @pytest.mark.parametrize(
            "pyproject_toml",
            [
                '''
                [tool.conhead.header.py]
                template = """
                    Template line 1
                    Template line 2
                """
                '''
            ],
        )
        def test_default_extensions(conhead_config):
            assert conhead_config == config.Config(
                headers=util.FrozenDict(
                    {
                        "py": config.Header(
                            name="py",
                            template="Template line 1\nTemplate line 2\n",
                            extensions=("py",),
                        )
                    }
                )
            )

        @staticmethod
        @pytest.mark.parametrize(
            "pyproject_toml",
            [
                '''
                [tool.conhead.header.py]
                extensions = ["ext1", "ext2"]
                template = """
                    Template line 1
                    Template line 2
                """
                '''
            ],
        )
        def test_explicit_extensions(conhead_config):
            assert conhead_config == config.Config(
                headers=util.FrozenDict(
                    {
                        "py": config.Header(
                            name="py",
                            template="Template line 1\nTemplate line 2\n",
                            extensions=("ext1", "ext2"),
                        )
                    }
                )
            )


class TestConfig:
    class TestExtensionLookup:
        @staticmethod
        @pytest.fixture
        def pyproject_toml() -> str:
            return """
                [tool.conhead.header.header1]
                template = ""
                extensions = ["ext1", "ext2"]

                [tool.conhead.header.header2]
                template = ""
                extensions = ["ext3", "ext4"]
                """

        class TestExtensionRe:
            @staticmethod
            @pytest.mark.parametrize("pyproject_toml", [None])
            def test_no_configuration(conhead_config):
                assert conhead_config.extensions_re is None

            @staticmethod
            def test_all_extensions(conhead_config):
                regex = conhead_config.extensions_re
                assert (
                    regex.pattern
                    == "(?P<header1>\\.(?:ext1|ext2)$)|(?P<header2>\\.(?:ext3|ext4)$)"
                )

                match = regex.search("path1/path2/file.ext1")
                assert match
                assert match.lastgroup == "header1"

                match = regex.search("path1/path2/file.ext2")
                assert match
                assert match.lastgroup == "header1"

                match = regex.search("path1/path2/file.ext3")
                assert match
                assert match.lastgroup == "header2"

                match = regex.search("path1/path2/file.ext4")
                assert match
                assert match.lastgroup == "header2"

        class TestHeaderForPath:
            @staticmethod
            def test_unknown_ext(conhead_config):
                assert (
                    conhead_config.header_for_path("path1/path2/file.unknown") is None
                )

            @staticmethod
            @pytest.mark.parametrize("pyproject_toml", [None])
            def test_empty_config(conhead_config):
                assert (
                    conhead_config.header_for_path("path1/path2/file.unknown") is None
                )

            @staticmethod
            def test_found_header(conhead_config):
                header = conhead_config.header_for_path("path1/path2/file.ext1")
                assert header
                assert header is conhead_config.headers["header1"]

                header = conhead_config.header_for_path("path1/path2/file.ext2")
                assert header
                assert header is conhead_config.headers["header1"]

                header = conhead_config.header_for_path("path1/path2/file.ext3")
                assert header
                assert header is conhead_config.headers["header2"]

                header = conhead_config.header_for_path("path1/path2/file.ext4")
                assert header
                assert header is conhead_config.headers["header2"]

    class TestFromDict:
        @staticmethod
        @pytest.mark.parametrize(
            "pyproject_toml",
            [
                """
                [tool.conhead]
                header = "header"
                """
            ],
        )
        def test_header_not_section():
            with pytest.raises(
                config.ConfigError, match=r"^tool.conhead.header must be section$"
            ):
                config.load()

        @staticmethod
        @pytest.mark.parametrize(
            "pyproject_toml",
            [
                """
                [tool.conhead.header]
                header1 = "header1"
                """
            ],
        )
        def test_header_definition_not_section():
            with pytest.raises(
                config.ConfigError,
                match=r"^tool.conhead.header.header1 must be section$",
            ):
                config.load()

        @staticmethod
        @pytest.mark.parametrize(
            "pyproject_toml",
            [
                """
                [tool.conhead]
                unexpected1 = "unexpected1"
                unexpected3 = "unexpected3"
                unexpected2 = "unexpected2"
                """
            ],
        )
        def test_unexpected_options():
            with pytest.raises(
                config.ConfigError,
                match=r"^unexpected options: unexpected1, unexpected2, unexpected3$",
            ):
                config.load()

        @staticmethod
        @pytest.mark.parametrize(
            "pyproject_toml",
            [
                """
                [tool.conhead.unexpected1]
                [tool.conhead.unexpected3]
                [tool.conhead.unexpected2]
                """
            ],
        )
        def test_unexpected_sections():
            with pytest.raises(
                config.ConfigError,
                match=r"^unexpected sections: unexpected1, unexpected2, unexpected3$",
            ):
                config.load()

        @staticmethod
        @pytest.mark.parametrize("pyproject_toml", ["other-options = 10"])
        def test_no_definitions():
            loaded = config.load()
            assert loaded == config.Config(headers=util.FrozenDict())


class TestFindPyproject:
    class TestFound:
        @staticmethod
        @pytest.fixture
        def project_dir_content() -> file_testing.DirContent:
            return {"pyproject.toml": "", "subdir1": {"subdir2": {}}}

        @staticmethod
        def test_find_from_root(project_dir):
            found = config.find_pyproject()
            assert found == project_dir / "pyproject.toml"

        @staticmethod
        def test_find_from_sub_dirs(project_dir):
            os.chdir(project_dir / "subdir1" / "subdir2")
            found = config.find_pyproject()
            assert found == project_dir / "pyproject.toml"

    @staticmethod
    def test_not_found(project_dir):
        assert config.find_pyproject() is None

    @staticmethod
    @pytest.mark.parametrize("project_dir_content", [{"pyproject.toml": {}}])
    def test_not_file(project_dir):
        assert config.find_pyproject() is None


class TestParse:
    @staticmethod
    @pytest.fixture
    def project_dir_content() -> file_testing.DirContent:
        return {
            "pyproject.toml": (
                """
                [config.content]
                name = "value"
                """
            )
        }

    @staticmethod
    def test_success():
        assert config.parse() == {"config": {"content": {"name": "value"}}}

    @staticmethod
    @pytest.mark.parametrize("project_dir_content", [{}])
    def test_not_found():
        assert config.parse() is None


class TestLoad:
    @staticmethod
    def test_not_found():
        assert config.load() is None

    @staticmethod
    @pytest.mark.parametrize(
        "pyproject_toml",
        [
            '''
                [tool.conhead.header.py]
                template = """
                  # Python header
                  # License X
                """

                [tool.conhead.header.toml]
                template = """
                  # Toml header
                  # License X
                """
            '''
        ],
    )
    def test_success():
        conhead_config = config.load()
        assert conhead_config
        assert conhead_config.headers.keys() == {"py", "toml"}

        assert conhead_config.headers["py"] == config.Header(
            name="py", template="# Python header\n# License X\n", extensions=("py",)
        )
        assert conhead_config.headers["toml"] == config.Header(
            name="toml",
            template="# Toml header\n# License X\n",
            extensions=("toml",),
        )

    @staticmethod
    @pytest.mark.parametrize(
        "pyproject_toml",
        [
            """
            tool = "tool"
            """
        ],
    )
    def test_tool_not_section():
        with pytest.raises(config.ConfigError, match=r"^tool must be section$"):
            config.load()

    @staticmethod
    @pytest.mark.parametrize(
        "pyproject_toml",
        [
            """
            [tool]
            conhead = "conhead"
            """
        ],
    )
    def test_conhead_not_section():
        with pytest.raises(config.ConfigError, match=r"^tool.conhead must be section$"):
            config.load()
