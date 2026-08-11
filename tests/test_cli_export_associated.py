from pathlib import Path

from click.testing import CliRunner

from imagedephi.main import imagedephi


def test_cli_export_associated(
    cli_runner: CliRunner,
    tmp_path: Path,
    data_dir: Path,
    test_image_svs: Path,
) -> None:
    """Exercise the CLI with --export-associated and verify output directory creation."""
    input_image = test_image_svs
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = cli_runner.invoke(
        imagedephi,
        [
            "run",
            str(input_image),
            "--output-dir",
            str(output_dir),
            "-e",
        ],
    )

    assert result.exit_code == 0
    associated_dirs = [d for d in output_dir.iterdir() if "Associated" in d.name and d.is_dir()]
    assert len(associated_dirs) == 1


def test_cli_export_associated_long_flag(
    cli_runner: CliRunner,
    tmp_path: Path,
    data_dir: Path,
    test_image_svs: Path,
) -> None:
    """Verify the long --export-associated flag creates the directory."""
    input_image = test_image_svs
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = cli_runner.invoke(
        imagedephi,
        [
            "run",
            str(input_image),
            "--output-dir",
            str(output_dir),
            "--export-associated",
        ],
    )

    assert result.exit_code == 0
    associated_dirs = [d for d in output_dir.iterdir() if "Associated" in d.name and d.is_dir()]
    assert len(associated_dirs) == 1
