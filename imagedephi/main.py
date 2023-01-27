from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TextIO
import webbrowser

import click
from hypercorn import Config
from hypercorn.asyncio import serve
import yaml

from imagedephi.async_utils import run_coroutine, wait_for_port
from imagedephi.gui import app, shutdown_event
from imagedephi.redact import RuleSource, build_ruleset, redact_images, show_redaction_plan


@click.group
def imagedephi() -> None:
    """Redact microscopy whole slide images."""


@imagedephi.command
@click.argument(
    "input-dir", type=click.Path(exists=True, file_okay=False, readable=True, path_type=Path)
)
@click.argument(
    "output-dir",
    type=click.Path(exists=True, file_okay=False, readable=True, writable=True, path_type=Path),
)
@click.option(
    "-r",
    "--override-rules",
    type=click.File("r"),
    help="Specify user-defined rules to override defaults",
)
def run(input_dir: Path, output_dir: Path, override_rules: TextIO | None):
    """Redact images in a folder according to given rule sets."""
    override_rule_set = (
        build_ruleset(yaml.safe_load(override_rules), RuleSource.OVERRIDE)
        if override_rules
        else None
    )
    redact_images(input_dir, output_dir, override_rule_set)


@imagedephi.command
@click.argument("image", type=click.Path())
@click.option(
    "-r",
    "--override-rules",
    type=click.File("r"),
    help="Specify user-defined rules to override defaults",
)
def redaction_plan(image: click.Path, override_rules: TextIO | None) -> None:
    """Print the redaction plan for a given image and rules."""
    override_rule_set = (
        build_ruleset(yaml.safe_load(override_rules), RuleSource.OVERRIDE)
        if override_rules
        else None
    )
    show_redaction_plan(image, override_rule_set)


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
