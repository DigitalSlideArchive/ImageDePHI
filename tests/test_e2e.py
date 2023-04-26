import asyncio
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
import datetime
from pathlib import Path
import sys

from click.testing import CliRunner
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


@pytest.mark.timeout(5)
def test_e2e_run(cli_runner: CliRunner, data_dir: Path, rules_dir: Path, tmp_path: Path) -> None:
    result = cli_runner.invoke(
        main.imagedephi,
        [
            "--override-rules",
            str(rules_dir / "example_user_rules.yml"),
            "run",
            str(data_dir / "input" / "tiff"),
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    time_stamp = datetime.datetime.now().isoformat(timespec="seconds")
    output_file = tmp_path / f"Redacted_{time_stamp}/REDACTED_test_image.tif"
    assert output_file.exists()
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
    time_stamp = datetime.datetime.now().isoformat(timespec="seconds")
    output_file = tmp_path / f"Redacted_{time_stamp}/REDACTED_test_image.tif"
    assert output_file.exists()
    output_file_bytes = output_file.read_bytes()
    assert b"large_image_converter" not in output_file_bytes
    assert f"127.0.0.1:{unused_tcp_port}" in webbrowser_open_mock.call_args.args[0]
    # Expect the client thread to be completed
    client_response = client_future.result(timeout=0)
    assert client_response.status_code == 200
    assert "You chose" in client_response.text


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
