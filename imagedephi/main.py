from __future__ import annotations

import asyncio
from pathlib import Path
import webbrowser

import click
from hypercorn import Config
from hypercorn.asyncio import serve

from imagedephi.async_utils import run_coroutine, wait_for_port
from imagedephi.gui import app, shutdown_event
from imagedephi.redact import redact_images


@click.group
def imagedephi() -> None:
    """Redact microscopy whole slide images."""
    pass


@imagedephi.command
@click.argument(
    "input-dir", type=click.Path(exists=True, file_okay=False, readable=True, path_type=Path)
)
@click.argument(
    "output-dir", type=click.Path(exists=True, file_okay=False, writable=True, path_type=Path)
)
def run(input_dir: Path, output_dir: Path) -> None:
    """Run in CLI-only mode."""
    redact_images(input_dir, output_dir)
    click.echo("Done!")


@imagedephi.command
@click.option(
    "--port",
    type=click.IntRange(1, 65535),
    default=8000,
    show_default=True,
    help="Local TCP port to run the GUI webserver on.",
)
@run_coroutine
async def gui(port: int) -> None:
    """Run a web-based GUI."""
    host = "127.0.0.1"

    server_config = Config()
    server_config.bind = [f"{host}:{port}"]
    serve_coro = serve(
        app,  # type: ignore
        server_config,
        shutdown_trigger=shutdown_event.wait,  # type: ignore
    )

    async def announce_ready() -> None:
        # To avoid race conditions, ensure that the webserver is
        # actually running before launching the browser
        await wait_for_port(port)
        url = f"http://{host}:{port}/"
        click.echo(f"Server is running at {url} .")
        webbrowser.open(url)

    await asyncio.gather(announce_ready(), serve_coro)
