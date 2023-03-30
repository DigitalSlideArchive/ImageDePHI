from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO
import webbrowser

import click
from hypercorn import Config
from hypercorn.asyncio import serve
import yaml

from imagedephi.async_utils import run_coroutine, wait_for_port
from imagedephi.gui import app, shutdown_event
from imagedephi.redact import redact_images, show_redaction_plan
from imagedephi.rules import RuleSet, RuleSource, build_ruleset


@dataclass
class ImagedephiContext:
    override_rule_set: RuleSet | None = None


@click.group
@click.option(
    "-r",
    "--override-rules",
    type=click.File("r"),
    help="User-defined rules to override defaults",
)
@click.pass_context
def imagedephi(ctx: click.Context, override_rules: TextIO | None) -> None:
    """Redact microscopy whole slide images."""
    obj = ImagedephiContext()
    # Store separately, to preserve the type of "obj"
    ctx.obj = obj

    if override_rules:
        obj.override_rule_set = build_ruleset(yaml.safe_load(override_rules), RuleSource.OVERRIDE)


@imagedephi.command
@click.argument("input-path", type=click.Path(exists=True, readable=True, path_type=Path))
@click.argument(
    "output-dir",
    type=click.Path(exists=True, file_okay=False, readable=True, writable=True, path_type=Path),
)
@click.option(
    "-o",
    "--overwrite-existing-output",
    is_flag=True,
    default=False,
    help="Overwrite previous output for input images",
)
@click.pass_obj
def run(
    obj: ImagedephiContext, input_path: Path, output_dir: Path, overwrite_existing_output: bool
):
    """Perform the redaction of images."""
    redact_images(input_path, output_dir, obj.override_rule_set, overwrite_existing_output)


@imagedephi.command
@click.argument("input-path", type=click.Path(exists=True, readable=True, path_type=Path))
@click.pass_obj
def plan(obj: ImagedephiContext, input_path: Path) -> None:
    """Print the redaction plan for images."""
    show_redaction_plan(input_path, obj.override_rule_set)


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
    """Launch a web-based GUI."""
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
