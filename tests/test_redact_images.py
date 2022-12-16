from pathlib import Path

from click.testing import CliRunner
import pytest

from imagedephi.__main__ import main


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def data_dir() -> Path:
    return Path(__file__).parent / "data"


def test_e2e(data_dir: Path, tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(main, [str(data_dir / "input"), str(tmp_path)])

    assert result.exit_code == 0
    output_file = tmp_path / "REDACTED_test_image.tif"
    assert output_file.exists()
    output_file_bytes = output_file.read_bytes()
    assert b"large_image_converter" not in output_file_bytes
    assert b"Redacted by ImageDePHI" in output_file_bytes
