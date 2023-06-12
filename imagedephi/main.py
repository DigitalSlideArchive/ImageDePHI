from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import TextIO
import webbrowser

import click
from hypercorn import Config
from hypercorn.asyncio import serve
from loguru import logger
import yaml

from imagedephi.gui import app, shutdown_event
from imagedephi.redact import redact_images, show_redaction_plan
from imagedephi.rules import Ruleset
from imagedephi.utils.cli import FallthroughGroup, run_coroutine
from imagedephi.utils.network import unused_tcp_port, wait_for_port
from imagedephi.utils.os import launched_from_windows_explorer


@dataclass
class ImagedephiContext:
    override_rule_set: Ruleset | None = None


CONTEXT_SETTINGS = {"help_option_names": ["--help"]}
if sys.platform == "win32":
    # Allow Windows users to get help via "/?".
    # To avoid ambiguity with actual paths, only support this on Windows.
    CONTEXT_SETTINGS["help_option_names"].append("/?")

# set default logger to warning level
logger.remove()
logger.add(sys.stderr, level="WARNING")


def set_logging_level(v: int, q: bool):
    if q:
        logger.remove()
        logger.add(sys.stderr, level="ERROR")
    else:
        match v:
            case 0:
                logger.remove()
                logger.add(sys.stderr, level="WARNING")
            case 1:
                logger.remove()
                logger.add(sys.stderr, level="INFO")
            case 2:
                logger.remove()
                logger.add(sys.stderr, level="DEBUG")


@click.group(
    cls=FallthroughGroup,
    subcommand_name="gui",
    should_fallthrough=launched_from_windows_explorer,
    context_settings=CONTEXT_SETTINGS,
)
@click.version_option(prog_name="ImageDePHI")
@click.option(
    "-r",
    "--override-rules",
    type=click.File("r"),
    help="User-defined rules to override defaults.",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="""\b
    Defaults to WARNING level logging
    -v  Show INFO level logging
    -vv Show DEBUG level logging""",
)
@click.option(
    "-q", "--quiet", is_flag=True, default=False, help="Show ERROR and CRITICAL level logging"
)
@click.pass_context
def imagedephi(ctx: click.Context, override_rules: TextIO | None, verbose, quiet) -> None:
    """Redact microscopy whole slide images."""
    obj = ImagedephiContext()
    # Store separately, to preserve the type of "obj"
    ctx.obj = obj

    if override_rules:
        obj.override_rule_set = Ruleset.parse_obj(yaml.safe_load(override_rules))

    set_logging_level(verbose, quiet)


@imagedephi.command
@click.argument("input-path", type=click.Path(exists=True, readable=True, path_type=Path))
@click.option(
    "-o",
    "--output-dir",
    default=Path.cwd(),
    show_default="current working directory",
    help="Path where output directory will be created.",
    type=click.Path(exists=True, file_okay=False, readable=True, writable=True, path_type=Path),
)
@click.pass_obj
def run(obj: ImagedephiContext, input_path: Path, output_dir: Path):
    """Perform the redaction of images."""
    redact_images(input_path, output_dir, obj.override_rule_set)


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
    default=unused_tcp_port,
    show_default="random unused port",
    help="Local TCP port to run the GUI webserver on.",
)
@run_coroutine
async def gui(port: int) -> None:
    """Launch a web-based GUI."""
    host = "127.0.0.1"

    # Disable Hypercorn sending logs directly to stdout / stderr
    server_config = Config.from_mapping(accesslog=None, errorlog=None)
    server_config.bind = [f"{host}:{port}"]

    async def announce_ready() -> None:
        # To avoid race conditions, ensure that the webserver is
        # actually running before launching the browser
        await wait_for_port(port)
        url = f"http://{host}:{port}/"
        click.echo(f"Server is running at {url} .")
        webbrowser.open(url)

    async with asyncio.TaskGroup() as task_group:
        task_group.create_task(announce_ready())
        task_group.create_task(
            serve(
                app,  # type: ignore
                server_config,
                shutdown_trigger=shutdown_event.wait,  # type: ignore
            )
        )
