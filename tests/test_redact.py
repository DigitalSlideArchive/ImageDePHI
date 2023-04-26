import datetime
from pathlib import Path, PurePath

import pytest
import yaml

from imagedephi import redact
from imagedephi.rules import RuleSource, build_ruleset


@pytest.fixture
def override_rule_set(data_dir):
    rule_file = data_dir / "rules" / "example_user_rules.yml"
    with rule_file.open() as rule_stream:
        return build_ruleset(yaml.safe_load(rule_stream), RuleSource.OVERRIDE)


@pytest.fixture(
    params=[PurePath("svs"), PurePath("svs") / "test_svs_image_blank.svs"],
    ids=["input_dir", "input_file"],
)
def svs_input_path(data_dir, request) -> Path:
    return data_dir / "input" / request.param


def test_redact_svs(svs_input_path, tmp_path, override_rule_set):
    redact.redact_images(svs_input_path, tmp_path, override_rule_set)

    time_stamp = datetime.datetime.now().isoformat(timespec="seconds")
    svs_output_file = tmp_path / f"Redacted_{time_stamp}/REDACTED_test_svs_image_blank.svs"
    assert svs_output_file.exists()
    svs_output_file_bytes = svs_output_file.read_bytes()
    # verify our custom svs rule was applied
    assert b"ICC Profile" not in svs_output_file_bytes


def test_plan_svs(capsys, svs_input_path, override_rule_set):
    redact.show_redaction_plan(svs_input_path, override_rule_set)

    captured = capsys.readouterr()
    assert "Replace ImageDescription" not in captured.out
    assert "Aperio (.svs) Metadata Redaction Plan" in captured.out
    assert "Delete ICC Profile" in captured.out
