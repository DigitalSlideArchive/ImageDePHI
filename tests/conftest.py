from pathlib import Path

import pytest


@pytest.fixture
def data_dir() -> Path:
    return Path(__file__).with_name("data")


@pytest.fixture
def rules_dir() -> Path:
    return Path(__file__).with_name("override_rule_sets")
