import pytest

from tests.conhead import file_testing


@pytest.fixture
def populated_pyproject_toml() -> str:
    return '''
            [tool.conhead.header.header1]
            extensions = ["ext1", "ext2"]
            template = """
                # line 1 {{YEAR}}
                # line 2 {{YEAR}}
            """

            [tool.conhead.header.header2]
            extensions = ["ext3", "ext4"]
            template = """
                // line 1 {{YEAR}}
                // line 2 {{YEAR}}
            """
        '''


@pytest.fixture
def populated_source_dir() -> file_testing.DirContent:
    return {
        "unreadable.ext1": file_testing.Perm("", read=False),
        "empty.ext1": "",
        "unmatched.unknown": "",
        "up-to-date.ext2": """\
                # line 1 2019
                # line 2 2014-2019
            """,
        "no-header.ext3": """\
                // No proper header
            """,
        "out-of-date.ext4": """\
                // line 1 2018
                // line 2 2014-2018
            """,
    }