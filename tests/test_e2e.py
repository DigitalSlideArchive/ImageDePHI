import asyncio
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from click.testing import CliRunner
import httpx
import pytest
from pytest_mock import MockerFixture

from imagedephi import main
from imagedephi.async_utils import wait_for_port


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def thread_executor() -> Generator[ThreadPoolExecutor, None, None]:
    executor = ThreadPoolExecutor(max_workers=1)
    yield executor
    executor.shutdown(cancel_futures=True)


@pytest.mark.timeout(5)
def test_e2e_run(runner: CliRunner, data_dir: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        main.imagedephi,
        [
            "--override-rules",
            str(data_dir / "rules" / "example_user_rules.yml"),
            "run",
            str(data_dir / "input" / "tiff"),
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    output_file = tmp_path / "REDACTED_test_image.tif"
    assert output_file.exists()
    output_file_bytes = output_file.read_bytes()
    assert b"large_image_converter" not in output_file_bytes
    assert b"Redacted by ImageDePHI" in output_file_bytes


@pytest.mark.timeout(5)
def test_e2e_plan(runner: CliRunner, data_dir: Path, tmp_path: Path) -> None:
    result = runner.invoke(
        main.imagedephi,
        [
            "--override-rules",
            str(data_dir / "rules" / "example_user_rules.yml"),
            "plan",
            str(data_dir / "input" / "tiff" / "test_image.tif"),
        ],
    )
    assert result.exit_code == 0
    assert "Replace ImageDescription" in result.stdout


@pytest.mark.timeout(5)
def test_e2e_gui(
    runner: CliRunner,
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

    cli_result = runner.invoke(main.imagedephi, ["gui", "--port", str(unused_tcp_port)])

    assert cli_result.exit_code == 0
    webbrowser_open_mock.assert_called_once()
    output_file = tmp_path / "REDACTED_test_image.tif"
    assert output_file.exists()
    output_file_bytes = output_file.read_bytes()
    assert b"large_image_converter" not in output_file_bytes
    assert f"127.0.0.1:{unused_tcp_port}" in webbrowser_open_mock.call_args.args[0]
    # Expect the client thread to be completed
    client_response = client_future.result(timeout=0)
    assert client_response.status_code == 200
    assert "You chose" in client_response.text
