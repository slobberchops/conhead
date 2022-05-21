import pytest
from click import testing


@pytest.fixture
def cli_runner():
    return testing.CliRunner()
