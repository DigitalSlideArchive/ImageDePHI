import asyncio
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys

from click.testing import CliRunner
from freezegun import freeze_time
import httpx
import pytest

from imagedephi import main
from imagedephi.utils.network import wait_for_port


@freeze_time("2023-05-12 12:12:53")
@pytest.mark.timeout(5)
def test_e2e_run(cli_runner: CliRunner, data_dir: Path, rules_dir: Path, tmp_path: Path) -> None:
    result = cli_runner.invoke(
        main.imagedephi,
        [
            "--override-rules",
            str(rules_dir / "example_user_rules.yml"),
            "run",
            str(data_dir / "input" / "tiff"),
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    output_file = tmp_path / "Redacted_2023-05-12_12-12-53" / "my_study_slide_1.tif"
    output_file_bytes = output_file.read_bytes()
    assert b"large_image_converter" not in output_file_bytes
    assert b"Redacted by ImageDePHI" in output_file_bytes


@pytest.mark.timeout(5)
def test_e2e_plan(cli_runner: CliRunner, data_dir: Path, rules_dir: Path) -> None:
    result = cli_runner.invoke(
        main.imagedephi,
        [
            "--override-rules",
            str(rules_dir / "example_user_rules.yml"),
            "plan",
            str(data_dir / "input" / "tiff" / "test_image.tif"),
        ],
    )

    assert result.exit_code == 0


def test_e2e_gui(
    unused_tcp_port: int,
    data_dir: Path,
    tmp_path: Path,
) -> None:

    port = unused_tcp_port

    gui = subprocess.Popen(
        [sys.executable, "-m", "imagedephi", "gui", "--port", str(port)],
    )

    asyncio.run(asyncio.wait_for(wait_for_port(port), timeout=2))

    # Check that the GUI is running
    assert gui.poll() is None

    check_gui = httpx.get(f"http://127.0.0.1:{port}")
    assert check_gui.status_code == 200

    # flake8: noqa: E501
    check_redact = httpx.post(
        f"http://127.0.0.1:{port}/redact/?input_directory={str(data_dir /'input' /'tiff')}&output_directory={str(tmp_path)}",
    )

    assert check_redact.status_code == 200

    gui.terminate()
    gui.wait()
    # Check that the GUI has stopped
    assert gui.poll() is not None

    redacted_dirs = list(tmp_path.glob("*Redacted*"))
    assert len(redacted_dirs) > 0
    redacted_files = list(redacted_dirs[0].glob("*"))
    assert len(redacted_files) > 0
    output_file = redacted_dirs[0] / "study_slide_1.tif"
    output_file_bytes = output_file.read_bytes()
    assert b"large_image_converter" not in output_file_bytes


def test_e2e_version(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(main.imagedephi, ["--version"])

    assert result.exit_code == 0
    assert "ImageDePHI, version" in result.output


@pytest.mark.parametrize(
    "help_flag",
    [
        "--help",
        pytest.param(
            "/?", marks=pytest.mark.skipif(sys.platform != "win32", reason="windows only")
        ),
    ],
)
def test_e2e_help(cli_runner: CliRunner, help_flag: str) -> None:
    result = cli_runner.invoke(main.imagedephi, [help_flag])

    assert result.exit_code == 0
    assert "Usage: imagedephi" in result.output


@freeze_time("2023-05-12 12:12:53")
@pytest.mark.timeout(5)
@pytest.mark.parametrize("rename", [True, False])
def test_e2e_rename_flag(cli_runner, data_dir: Path, tmp_path: Path, rename: bool):
    rename_flag = "--rename" if rename else "--skip-rename"
    result = cli_runner.invoke(
        main.imagedephi,
        ["run", str(data_dir / "input" / "tiff"), "--output-dir", str(tmp_path), rename_flag],
    )

    assert result.exit_code == 0

    output_file_name = (
        tmp_path / "Redacted_2023-05-12_12-12-53" / "study_slide_1.tif"
        if rename
        else tmp_path / "Redacted_2023-05-12_12-12-53" / "test_image.tif"
    )
    assert output_file_name.exists()


@freeze_time("2024-01-04 10:48:00")
@pytest.mark.timeout(5)
@pytest.mark.parametrize(
    "recursive,rename", [(True, True), (True, False), (False, False), (False, True)]
)
def test_e2e_recursive(cli_runner, data_dir: Path, tmp_path: Path, recursive: bool, rename: bool):
    args = ["run", str(data_dir / "input"), "--output-dir", str(tmp_path)]
    if recursive:
        args.append("--recursive")
    if rename:
        args.append("--skip-rename")
    result = cli_runner.invoke(main.imagedephi, args)

    assert result.exit_code == 0
    output_subdir = tmp_path / "Redacted_2024-01-04_10-48-00" / "svs"
    assert output_subdir.exists() == recursive

    if recursive:
        assert len(list(output_subdir.iterdir()))
