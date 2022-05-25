import datetime
import os
import pathlib
from typing import Iterable
from typing import Iterator
from typing import Optional

import pytest
from click import testing

from conhead import config
from conhead import main
from conhead import util
from tests.conhead import file_testing
from tests.conhead.test_process import NOW


@pytest.fixture
def cli_runner() -> testing.CliRunner:
    return testing.CliRunner()


@pytest.fixture
def pyproject_toml() -> Optional[str]:
    return None


@pytest.fixture
def source_dir() -> Optional[file_testing.DirContent]:
    return None


@pytest.fixture
def project_dir_content(pyproject_toml, source_dir) -> file_testing.DirContent:
    return {"pyproject.toml": pyproject_toml, "src": source_dir}


@pytest.fixture(autouse=True)
def project_dir(tmp_path, project_dir_content) -> Iterator[pathlib.Path]:
    project_dir = tmp_path / "project"
    file_testing.write_content_dir(project_dir, project_dir_content)
    cwd = pathlib.Path.cwd()
    try:
        os.chdir(project_dir)
        yield project_dir
    finally:
        os.chdir(cwd)


@pytest.fixture
def conhead_config(pyproject_toml) -> config.Config:
    return config.load() or config.Config(headers=util.FrozenDict())


@pytest.fixture
def fake_time() -> Iterable[None]:
    original_now = main.naive_now
    try:

        def fake_now() -> Iterator[datetime.datetime]:
            yield NOW

        iterator = fake_now()
        main.naive_now = lambda: next(iterator)
        yield
    finally:
        main.naive_now = original_now
