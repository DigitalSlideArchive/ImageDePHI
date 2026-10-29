"""Exercise a built (PyInstaller) imagedephi binary, as distributed to users.

These are skipped unless pytest is given "--binary PATH", e.g. via "tox -e test-binary".
"""

import asyncio
from io import BytesIO
from pathlib import Path
import re
import shutil
import subprocess
import sys

from PIL import Image
import httpx
import pytest

from imagedephi.utils.network import wait_for_port

# One-file binaries unpack themselves on every launch, which is slow on some platforms
STARTUP_TIMEOUT = 120


@pytest.fixture
def binary(request: pytest.FixtureRequest) -> Path:
    path: Path | None = request.config.getoption("--binary")
    if path is None:
        pytest.skip("No --binary given")
    if not path.exists() and sys.platform == "win32":
        path = path.with_suffix(".exe")
    assert path.is_file(), f"Binary not found: {path}"
    return path.resolve()


@pytest.fixture
def input_dir(
    tmp_path: Path, test_image_tiff: Path, test_image_svs: Path, test_image_dcm: list[Path]
) -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    for image in [test_image_tiff, test_image_svs, *test_image_dcm]:
        shutil.copy(image, input_dir)
    return input_dir


def run_binary(binary: Path, *args: str | Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [binary, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=STARTUP_TIMEOUT * 2,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return result


def single_match(directory: Path, pattern: str) -> Path:
    matches = list(directory.glob(pattern))
    assert len(matches) == 1, f"Expected one {pattern} in {directory}, found {matches}"
    return matches[0]


def assert_redacted(redacted_dir: Path) -> None:
    tiff_bytes = single_match(redacted_dir, "*.tif").read_bytes()
    assert b"large_image_converter" not in tiff_bytes
    svs_bytes = single_match(redacted_dir, "*.svs").read_bytes()
    assert b"Aperio" in svs_bytes
    assert b"ScanScope ID" not in svs_bytes
    dcm_bytes = single_match(redacted_dir, "*.dcm").read_bytes()
    assert b"DICM" in dcm_bytes
    assert b"Sample" not in dcm_bytes


def test_binary_help(binary: Path) -> None:
    result = run_binary(binary, "--help")

    assert "Usage:" in result.stdout


def test_binary_version(binary: Path) -> None:
    result = run_binary(binary, "--version")

    assert "ImageDePHI, version" in result.stdout


def test_binary_plan(binary: Path, input_dir: Path) -> None:
    result = run_binary(binary, "plan", input_dir)

    for image in input_dir.iterdir():
        assert f"Redaction plan for {image.name}" in result.stdout


def test_binary_run(binary: Path, input_dir: Path, rules_dir: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    run_binary(
        binary,
        "run",
        input_dir,
        "--output-dir",
        output_dir,
        "-R",
        rules_dir / "example_user_rules.yaml",
        "--export-associated",
    )

    redacted_dir = single_match(output_dir, "Redacted_*[0-9]")
    assert_redacted(redacted_dir)
    # Added by the override rules
    assert b"Redacted by ImageDePHI" in single_match(redacted_dir, "*.tif").read_bytes()
    single_match(output_dir, "Redacted_*_manifest.csv")
    associated_images = list(single_match(output_dir, "Associated_*").rglob("*.jpg"))
    assert associated_images
    for associated_image in associated_images:
        with Image.open(associated_image) as image:
            image.verify()


async def wait_for_server(process: subprocess.Popen, port: int) -> None:
    """Wait for the server to listen on port, failing early if it exits first."""
    port_task = asyncio.create_task(wait_for_port(port))
    loop = asyncio.get_running_loop()
    deadline = loop.time() + STARTUP_TIMEOUT
    while not port_task.done():
        assert process.poll() is None, f"Server exited with code {process.returncode}"
        assert loop.time() < deadline, "Timed out waiting for server to start"
        await asyncio.wait([port_task], timeout=0.5)
    port_task.result()


def test_binary_gui(binary: Path, input_dir: Path, unused_tcp_port: int, tmp_path: Path) -> None:
    port = unused_tcp_port
    base_url = f"http://127.0.0.1:{port}"
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    gui = subprocess.Popen([binary, "gui", "--port", str(port), "--no-browser"])
    try:
        asyncio.run(wait_for_server(gui, port))

        with httpx.Client(base_url=base_url, timeout=STARTUP_TIMEOUT) as client:
            # The bundled web client and its assets are served
            index = client.get("/")
            assert index.status_code == 200
            assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', index.text)
            assert assets
            for asset in assets:
                assert client.get(asset).status_code == 200

            directory = client.get("/directory/", params={"directory": str(input_dir)})
            assert directory.status_code == 200

            thumbnail = client.get(
                "/image/",
                params={
                    "file_name": str(input_dir / "test_svs_image_blank.svs"),
                    "image_key": "thumbnail",
                },
            )
            assert thumbnail.status_code == 200
            assert thumbnail.headers["content-type"] == "image/jpeg"
            with Image.open(BytesIO(thumbnail.content)) as image:
                image.verify()

            redact = client.post(
                "/redact/",
                params={"input_directory": str(input_dir), "output_directory": str(output_dir)},
            )
            assert redact.status_code == 200

        assert gui.poll() is None
    finally:
        gui.terminate()
        gui.wait(timeout=30)

    assert_redacted(single_match(output_dir, "Redacted_*[0-9]"))
