import pytest
import yaml

from imagedephi import redact
from imagedephi.rules import RuleSource, build_ruleset


@pytest.fixture
def override_rule_set(data_dir):
    rule_file = data_dir / "rules" / "example_user_rules.yml"
    with rule_file.open() as rule_stream:
        return build_ruleset(yaml.safe_load(rule_stream), RuleSource.OVERRIDE)


def test_redact_svs_dir(data_dir, tmp_path, override_rule_set):
    redact.redact_images(data_dir / "input" / "svs", tmp_path, override_rule_set)

    svs_output_file = tmp_path / "REDACTED_test_svs_image_blank.svs"
    assert svs_output_file.exists()
    svs_output_file_bytes = svs_output_file.read_bytes()
    # verify our custom svs rule was applied
    assert b"ICC Profile" not in svs_output_file_bytes


def test_redact_svs_file(data_dir, tmp_path, override_rule_set):
    redact.redact_images(
        data_dir / "input" / "svs" / "test_svs_image_blank.svs", tmp_path, override_rule_set
    )

    svs_output_file = tmp_path / "REDACTED_test_svs_image_blank.svs"
    assert svs_output_file.exists()
    svs_output_file_bytes = svs_output_file.read_bytes()
    # verify our custom svs rule was applied
    assert b"ICC Profile" not in svs_output_file_bytes


def test_plan_svs_dir(capsys, data_dir, tmp_path, override_rule_set):
    redact.show_redaction_plan(data_dir / "input" / "svs", override_rule_set)
    captured = capsys.readouterr()
    assert "Replace ImageDescription" not in captured.out
    assert "Aperio (.svs) Metadata Redaction Plan" in captured.out
    assert "Delete ICC Profile" in captured.out


def test_plan_svs_file(capsys, data_dir, tmp_path, override_rule_set):
    redact.show_redaction_plan(
        data_dir / "input" / "svs" / "test_svs_image_blank.svs", override_rule_set
    )
    captured = capsys.readouterr()
    assert "Replace ImageDescription" not in captured.out
    assert "Aperio (.svs) Metadata Redaction Plan" in captured.out
    assert "Delete ICC Profile" in captured.out
