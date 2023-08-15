import importlib.resources
import logging
from pathlib import Path, PurePath

from freezegun import freeze_time
import pytest
import yaml

from imagedephi import redact
from imagedephi.redact.redact import create_redact_dir
from imagedephi.redact.svs import SvsRedactionPlan
from imagedephi.rules import Ruleset
from imagedephi.utils.logger import logger


@pytest.fixture
def base_rule_set():
    base_rules_path = importlib.resources.files("imagedephi") / "base_rules.yaml"
    with base_rules_path.open() as base_rules_stream:
        return Ruleset.parse_obj(yaml.safe_load(base_rules_stream))


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


@freeze_time("2023-05-12 12:12:53")
def test_create_redact_dir(tmp_path):
    output_dir = create_redact_dir(tmp_path / "fake")
    assert output_dir.exists()
    assert output_dir.name == "Redacted_2023-05-12_12-12-53"


@freeze_time("2023-05-12 12:12:53")
def test_redact_svs(svs_input_path, tmp_path, override_rule_set):
    redact.redact_images(svs_input_path, tmp_path, override_rule_set)

    output_file = tmp_path / "Redacted_2023-05-12_12-12-53" / "my_study_slide_1.svs"
    svs_output_file_bytes = output_file.read_bytes()
    # verify our custom svs rule was applied
    assert b"ICC Profile" not in svs_output_file_bytes
    # verify the base image rule was applied to the macro
    assert b"macro" not in svs_output_file_bytes


def test_plan_svs(caplog, svs_input_path, override_rule_set):
    logger.setLevel(logging.INFO)
    redact.show_redaction_plan(svs_input_path, override_rule_set)

    assert "Aperio (.svs) Metadata Redaction Plan" in caplog.text
    assert "ICC Profile: delete" in caplog.text


def test_associated_image_key_no_description(data_dir, base_rule_set):
    input_image = data_dir / "input" / "svs" / "test_svs_image_blank.svs"
    svs_redaction_plan = SvsRedactionPlan(input_image, base_rule_set.svs)
    test_tags = {
        254: {
            "datatype": 4,
            "count": 1,
            "datapos": 0,
            "data": [9],
        }
    }
    test_ifd = {
        "offset": 0,
        "tags": test_tags,
        "path_or_fobj": "",
        "size": 0,
        "bigEndian": False,
        "bigtiff": False,
        "tagcount": 1,
    }
    associated_image_key = svs_redaction_plan.get_associated_image_key_for_ifd(
        test_ifd,  # type: ignore
    )
    assert associated_image_key == "macro"
