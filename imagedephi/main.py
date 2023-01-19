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
from imagedephi.redact import (
    build_ruleset,
    redact_images,
    redact_images_using_rules,
    show_redaction_plan,
)


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
@click.argument(
    "input-dir", type=click.Path(exists=True, file_okay=False, readable=True, path_type=Path)
)
@click.argument(
    "output-dir", type=click.Path(exists=True, file_okay=False, readable=True, path_type=Path)
)
@click.argument("base-rules", type=click.File("r"))
@click.argument("override-rules", type=click.File("r"))
def run_rules(input_dir: Path, output_dir: Path, base_rules: TextIO, override_rules: TextIO):
    """Redact images in a folder according to given rule sets."""
    base_rule_set, override_rule_set = [
        build_ruleset(yaml.safe_load(rules)) for rules in [base_rules, override_rules]
    ]
    redact_images_using_rules(input_dir, output_dir, base_rule_set, override_rule_set)


@imagedephi.command
@click.argument("image", type=click.Path())
@click.argument("base-rules", type=click.File("r"))
@click.argument("override-rules", type=click.File("r"))
def redaction_plan(image: click.Path, base_rules: TextIO, override_rules: TextIO) -> None:
    """Print the redaction plan for a given image and rules."""
    base_rule_set, override_rule_set = [
        build_ruleset(yaml.safe_load(rules)) for rules in [base_rules, override_rules]
    ]
    show_redaction_plan(image, base_rule_set, override_rule_set)


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
