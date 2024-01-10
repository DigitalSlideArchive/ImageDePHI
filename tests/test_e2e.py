import asyncio
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

from click.testing import CliRunner
from freezegun import freeze_time
import httpx
import pytest
from pytest_mock import MockerFixture

from imagedephi import main
from imagedephi.utils.network import wait_for_port


@pytest.fixture
def thread_executor() -> Generator[ThreadPoolExecutor, None, None]:
    executor = ThreadPoolExecutor(max_workers=1)
    yield executor
    executor.shutdown(cancel_futures=True)


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


@freeze_time("2023-05-12 12:12:53")
@pytest.mark.timeout(5)
def test_e2e_gui(
    cli_runner: CliRunner,
    unused_tcp_port: int,
    data_dir: Path,
    tmp_path: Path,
    thread_executor: ThreadPoolExecutor,
    mocker: MockerFixture,
) -> None:
    def client_select_directory(port: int) -> httpx.Response:
        # It's probably overkill to start an event loop,
        # but wait_for_port provides exactly what's needed here.
        # Use a timeout so a failing test won't be held up by this thread.
        asyncio.run(asyncio.wait_for(wait_for_port(port), timeout=2))
        return httpx.post(
            f"http://127.0.0.1:{port}/redact/",
            data={
                "input_directory": str(data_dir / "input" / "tiff"),
                "output_directory": str(tmp_path),
            },
        )

    webbrowser_open_mock = mocker.patch("webbrowser.open")
    # Ideally, we'd be able to use a running event loop to schedule the client
    # requests. However, the CLI starts its own event loop, then blocks until
    # completion. We could hook into or patch internal application events to
    # get a callback with an already-running event loop, but that provides less
    # isolation than just running the client in an independent thread.
    # Note, Click's CliRunner expects to run in a single-threaded environment,
    # but the new thread won't use any of the patched stdout, etc. streams and
    # a ProcessPoolExecutor is slower and requires more delicate pickling. so
    # we'll break that expection here.
    client_future = thread_executor.submit(client_select_directory, unused_tcp_port)

    cli_result = cli_runner.invoke(main.imagedephi, ["gui", "--port", str(unused_tcp_port)])
    # If an HTTP request is successfully sent, either the normal response from this endpoint or a
    # 500 error should cause the CLI to halt. However, if halting fails, then this test is
    # particularly susceptible to exceeding the timeout, which on Windows will crash pytest (due
    # to the behavior of pytest-timeout).

    assert cli_result.exit_code == 0
    webbrowser_open_mock.assert_called_once()
    output_file = tmp_path / "Redacted_2023-05-12_12-12-53" / "study_slide_1.tif"
    output_file_bytes = output_file.read_bytes()
    assert b"large_image_converter" not in output_file_bytes
    assert f"127.0.0.1:{unused_tcp_port}" in webbrowser_open_mock.call_args.args[0]
    # Expect the client thread to be completed
    client_response = client_future.result(timeout=0)
    assert client_response.status_code == 200


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
