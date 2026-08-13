from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from imagedephi.main import imagedephi


class UsageMock(SimpleNamespace):
    """Mock for shutil.disk_usage namedtuple."""

    def __init__(self, free: int) -> None:
        super().__init__(free=free)


def test_cli_refuses_redaction_when_space_insufficient(
    cli_runner: CliRunner, tmp_path: Path, test_image_svs: Path
) -> None:
    """Verify the CLI exits with an error when free disk space is below the default 10GB buffer."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Mocking available space to only 5GB (less than 10GB buffer)
    with patch("imagedephi.main.shutil.disk_usage", return_value=UsageMock(free=5 * (1024**3))):
        result = cli_runner.invoke(
            imagedephi,
            [
                "run",
                str(test_image_svs),
                "--output-dir",
                str(output_dir),
            ],
        )

    assert result.exit_code != 0
    assert "Insufficient disk space" in result.output


def test_cli_runs_when_space_above_buffer(
    cli_runner: CliRunner, tmp_path: Path, test_image_svs: Path
) -> None:
    """Verify CLI proceeds when enough space is available (mocking >10GB + input size)."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    with patch(
        "imagedephi.main.shutil.disk_usage",
        return_value=UsageMock(free=50 * (1024**3)),  # Plenty of space
    ):
        result = cli_runner.invoke(
            imagedephi,
            [
                "run",
                str(test_image_svs),
                "--output-dir",
                str(output_dir),
            ],
        )

    assert "Insufficient disk space" not in result.output


def test_cli_respects_custom_min_available_space(
    cli_runner: CliRunner, tmp_path: Path, test_image_svs: Path
) -> None:
    """Test that the user can override the default 10GB buffer via command line."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Available is 5GB. Default fails (needs 10). But with --min-available-space 1.0 it should pass!
    with patch("imagedephi.main.shutil.disk_usage", return_value=UsageMock(free=5 * (1024**3))):
        result = cli_runner.invoke(
            imagedephi,
            [
                "run",
                str(test_image_svs),
                "--output-dir",
                str(output_dir),
                "--min-available-space",
                "1.0",
            ],
        )

    assert "Insufficient disk space" not in result.output
