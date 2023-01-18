from pathlib import Path

from click.testing import CliRunner
import pytest

from imagedephi import main


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_e2e_run(data_dir: Path, tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(main.imagedephi, ["run", str(data_dir / "input"), str(tmp_path)])

    assert result.exit_code == 0
    output_file = tmp_path / "REDACTED_test_image.tif"
    assert output_file.exists()
    output_file_bytes = output_file.read_bytes()
    assert b"large_image_converter" not in output_file_bytes
    assert b"Redacted by ImageDePHI" in output_file_bytes
