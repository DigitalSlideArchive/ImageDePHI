from pathlib import Path

from click.testing import CliRunner
import pytest


@pytest.fixture
def data_dir() -> Path:
    return Path(__file__).with_name("data")


@pytest.fixture
def rules_dir() -> Path:
    return Path(__file__).with_name("override_rule_sets")


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()
