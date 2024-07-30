import importlib.resources
import logging
from pathlib import Path, PurePath

from freezegun import freeze_time
import pytest
import yaml

from imagedephi import redact
from imagedephi.redact.redact import ProfileChoice, create_redact_dir_and_manifest
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
    rule_file = rules_dir / "example_user_rules.yaml"
    with rule_file.open() as rule_stream:
        return Ruleset.parse_obj(yaml.safe_load(rule_stream))


@pytest.fixture(
    params=[PurePath("svs"), PurePath("svs") / "test_svs_image_blank.svs"],
    ids=["input_dir", "input_file"],
)
def svs_input_path(test_image_svs, data_dir, request) -> Path:
    return data_dir / "input" / request.param


@pytest.fixture(
    params=[PurePath("dcm"), PurePath("dcm") / "test_dcm_image.dcm"],
    ids=["input_dir", "input_file"],
)
def dcm_input_path(data_dir, test_image_dcm, request) -> Path:
    return data_dir / "input" / request.param


@freeze_time("2023-05-12 12:12:53")
def test_create_redact_dir_and_manifest(tmp_path):
    output_dir, manifest = create_redact_dir_and_manifest(tmp_path / "fake")
    assert output_dir.exists()
    assert output_dir.name == "Redacted_2023-05-12_12-12-53"
    assert manifest.exists()
    assert manifest.name == "Redacted_2023-05-12_12-12-53_manifest.csv"


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


@freeze_time("2023-05-12 12:12:53")
def test_remove_orphaned_metadata(secret_metadata_image, tmp_path, override_rule_set):
    input_bytes = secret_metadata_image.read_bytes()

    redact.redact_images(secret_metadata_image, tmp_path, override_rule_set)

    output_file = tmp_path / "Redacted_2023-05-12_12-12-53" / "my_study_slide_1.tiff"
    output_bytes = output_file.read_bytes()

    assert b"Secret" in input_bytes
    assert b"Secret" not in output_bytes


@freeze_time("2023-05-12 12:12:53")
def test_redact_dcm(test_image_dcm, tmp_path, override_rule_set):
    redact.redact_images(test_image_dcm, tmp_path, override_rule_set)

    output_file = tmp_path / "Redacted_2023-05-12_12-12-53" / "my_study_slide_1.dcm"
    dcm_output_file_bytes = output_file.read_bytes()
    # verify th ebase rule deleted "SeriesDescription"
    assert b"Sample" not in dcm_output_file_bytes


def test_plan_dcm(caplog, test_image_dcm):
    logger.setLevel(logging.INFO)
    redact.show_redaction_plan(test_image_dcm)

    assert "DICOM Metadata Redaction Plan" in caplog.text
    assert "SeriesDescription: delete" in caplog.text


@freeze_time("2023-05-12 12:12:53")
@pytest.mark.timeout(5)
def test_strict(svs_input_path, tmp_path) -> None:
    redact.redact_images(svs_input_path, tmp_path, profile=ProfileChoice.Strict.value)
    output_file = tmp_path / "Redacted_2023-05-12_12-12-53" / "study_slide_1.svs"
    output_file_bytes = output_file.read_bytes()
    assert b"Aperio" not in output_file_bytes
    assert b"macro" not in output_file_bytes


@freeze_time("2023-05-12 12:12:53")
@pytest.mark.timeout(5)
def test_strict_skip_dcm(dcm_input_path, tmp_path) -> None:
    redact.redact_images(dcm_input_path, tmp_path, profile=ProfileChoice.Strict.value)
    output_dir = tmp_path / "Redacted_2023-05-12_12-12-53"
    assert output_dir.is_dir()
    assert len(list(output_dir.iterdir())) == 0


@freeze_time("2023-05-12 12:12:53")
@pytest.mark.timeout(5)
def test_dates_dcm(test_image_dcm, tmp_path) -> None:
    redact.redact_images(test_image_dcm, tmp_path, profile=ProfileChoice.Dates.value)
    output_file = tmp_path / "Redacted_2023-05-12_12-12-53" / "study_slide_1.dcm"
    dcm_output_file_bytes = output_file.read_bytes()
    assert b"20220101" in dcm_output_file_bytes


@freeze_time("2023-05-12 12:12:53")
@pytest.mark.timeout(5)
def test_dates_svs(svs_input_path, tmp_path) -> None:
    redact.redact_images(svs_input_path, tmp_path, profile=ProfileChoice.Dates.value)
    output_file = tmp_path / "Redacted_2023-05-12_12-12-53" / "study_slide_1.svs"
    output_file_bytes = output_file.read_bytes()
    # DAte set to January 1
    assert b"01/01/08" in output_file_bytes
    # Time set to midnight
    assert b"00:00:00" in output_file_bytes
