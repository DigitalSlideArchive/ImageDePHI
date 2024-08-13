from pathlib import Path

from click.testing import CliRunner
import pooch
import pytest

registry = {
    "secret_metadata.tiff": "sha512:28be4880984bbb5f8e2a2e2314e594686427aa3da54e6a804ed5682e2da2585d21d3e3f751e995ad5b133a8b183cc7eb3cdee55cfcf5e4589d69c543db10fa9e",  # noqa: E501
    "test_dcm_image.dcm": "sha512:c3c39e133988f29a99d87107f3b8fbef1c6f530350a9192671f237862731d6f44d18965773a499867d853cbf22aaed9ea1670ce0defda125efe6a8c0cc63c316",  # noqa: E501
    "test_image.tif": "sha512:269d974a373f08e3274a1074fa595f8c70c496c64590412b6233eb2e3ce691c92963e5d0a3518848f15d9353783624faab18a002a9e049691cb5b627e40c9423",  # noqa: E501
    "test_svs_image_blank.svs": "sha512:76350f39bafd86ced9d94b9a095200d3894034c36a3bc9a45a57a8f5ea820b8fd877ae483e9d9d4aef018cd8ca96c54ea815467ec94f6d692fca0ecc69afab23",  # noqa: E501
}


def retrieve_file(file_name: str, output_path: Path) -> Path:
    algo, hash_value = registry[file_name].split(":")
    h = registry[file_name]
    full_path = pooch.retrieve(
        url=f"https://data.kitware.com/api/v1/file/hashsum/{algo}/{hash_value}/download",
        known_hash=h,
        fname=file_name,
        path=output_path,
    )
    return Path(full_path)


@pytest.fixture
def secret_metadata_image() -> Path:
    return retrieve_file("secret_metadata.tiff", Path(__file__).with_name("data") / "input")


@pytest.fixture
def test_image_tiff() -> Path:
    return retrieve_file("test_image.tif", Path(__file__).with_name("data") / "input" / "tiff")


@pytest.fixture
def test_image_svs() -> Path:
    return retrieve_file(
        "test_svs_image_blank.svs", Path(__file__).with_name("data") / "input" / "svs"
    )


@pytest.fixture
def test_image_dcm() -> Path:
    return retrieve_file("test_dcm_image.dcm", Path(__file__).with_name("data") / "input" / "dcm")


@pytest.fixture
def data_dir() -> Path:
    return Path(__file__).with_name("data")


@pytest.fixture
def rules_dir() -> Path:
    return Path(__file__).with_name("override_rule_sets")


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()
