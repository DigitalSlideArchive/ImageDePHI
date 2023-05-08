from pathlib import Path, PurePath

import pytest
import yaml

from imagedephi import redact
from imagedephi.rules import Ruleset


@pytest.fixture
def override_rule_set(rules_dir: Path):
    rule_file = rules_dir / "example_user_rules.yml"
    with rule_file.open() as rule_stream:
        return Ruleset.parse_obj(yaml.safe_load(rule_stream))


@pytest.fixture(
    params=[PurePath("svs"), PurePath("svs") / "test_svs_image_blank.svs"],
    ids=["input_dir", "input_file"],
)
def svs_input_path(data_dir, request) -> Path:
    return data_dir / "input" / request.param


def test_redact_svs(svs_input_path, tmp_path, override_rule_set):
    redact.redact_images(svs_input_path, tmp_path, override_rule_set)

    svs_output_file = tmp_path / "REDACTED_test_svs_image_blank.svs"
    assert svs_output_file.exists()
    svs_output_file_bytes = svs_output_file.read_bytes()
    # verify our custom svs rule was applied
    assert b"ICC Profile" not in svs_output_file_bytes


def test_redact_svs_image(data_dir, tmp_path):
    redact.redact_images(data_dir / "input" / "svs" / "test_svs_image_blank.svs", tmp_path)

    svs_output_file = tmp_path / "REDACTED_test_svs_image_blank.svs"
    svs_output_file_bytes = svs_output_file.read_bytes()
    # verify the base image rule was applied to the macro
    assert b"macro" not in svs_output_file_bytes


def test_plan_svs(capsys, svs_input_path, override_rule_set):
    redact.show_redaction_plan(svs_input_path, override_rule_set)

    captured = capsys.readouterr()
    assert "Aperio (.svs) Metadata Redaction Plan" in captured.out
    assert "ICC Profile: delete" in captured.out
