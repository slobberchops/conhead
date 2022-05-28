# Copyright 2022 Rafe Kaplan
# SPDX-License-Identifier: Apache-2.0

import pytest

from tests.conhead import file_testing


@pytest.fixture
def populated_pyproject_toml() -> str:
    return '''
            [tool.conhead.header.header1]
            extensions = ["ext1", "ext2"]
            template = """
                # line 1 {{YEARS}}
                # line 2 {{YEARS}}
            """

            [tool.conhead.header.header2]
            extensions = ["ext3", "ext4"]
            template = """
                // line 1 {{YEARS}}
                // line 2 {{YEARS}}
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
                content
            """,
        "sub-dir": {
            "file1.ext1": """\
                # line 1 2019
                # line 2 2014-2019
                file1
            """,
            "file2.ext3": """\
                // line 1 2019
                // line 2 2014-2019
                file3
            """,
            "file3.unknown": "file3",
        },
    }
