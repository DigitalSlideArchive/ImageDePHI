from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from pathlib import Path
import sys
from typing import TextIO
import webbrowser

import click
from hypercorn import Config
from hypercorn.asyncio import serve
import yaml

from imagedephi.gui.app import app
from imagedephi.redact import ProfileChoice, redact_images, show_redaction_plan
from imagedephi.rules import Ruleset
from imagedephi.utils.cli import FallthroughGroup, run_coroutine
from imagedephi.utils.logger import logger
from imagedephi.utils.network import unused_tcp_port, wait_for_port
from imagedephi.utils.os import launched_from_windows_explorer

shutdown_event = asyncio.Event()


_global_options = [
    click.option(
        "-v",
        "--verbose",
        count=True,
        help="""\b
        Defaults to WARNING level logging
        -v  Show INFO level logging
        -vv Show DEBUG level logging""",
    ),
    click.option("-q", "--quiet", count=True, help="Show ERROR and CRITICAL level logging"),
    click.option(
        "-l",
        "--log-file",
        help="Path where log file will be created",
        type=click.Path(path_type=Path),
    ),
    click.option(
        "-r", "--recursive", is_flag=True, help="Apply the command to images in subdirectories"
    ),
    click.option(
        "-p",
        "--profile",
        type=click.Choice([choice.value for choice in ProfileChoice], case_sensitive=False),
        help="Select a redaction profile. This determines the base rule set used for a run of the"
        " program.\n\nThe 'strict' profile currently only supports tiff and svs files, and will "
        " keep only metadata necessary to conform to the tiff standard.\n\nThe 'dates' profile will"
        " fuzz dates and times by setting to January 1st or midnight.\n\nThe 'default' profile uses"
        " our standard base rules, and is the default profile used.",
        default=ProfileChoice.Default.value,
    ),
]


def global_options(func):
    for option in _global_options:
        func = option(func)
    return func


@dataclass
class ImagedephiContext:
    override_rule_set: Ruleset | None = None


CONTEXT_SETTINGS = {"help_option_names": ["--help"]}
if sys.platform == "win32":
    # Allow Windows users to get help via "/?".
    # To avoid ambiguity with actual paths, only support this on Windows.
    CONTEXT_SETTINGS["help_option_names"].append("/?")


def set_logging_config(v: int, q: int, log_file: Path | None = None):
    logger.setLevel(max(1, logging.WARNING - 10 * (v - q)))
    if log_file:
        logger.handlers.clear()
        file_handler = logging.FileHandler(log_file)
        logger.addHandler(file_handler)


@click.group(
    cls=FallthroughGroup,
    subcommand_name="gui",
    should_fallthrough=launched_from_windows_explorer,
    context_settings=CONTEXT_SETTINGS,
)
@click.version_option(prog_name="ImageDePHI")
@click.option(
    "-R",
    "--override-rules",
    type=click.File("r"),
    help="User-defined rules to override defaults.",
)
@global_options
@click.pass_context
def imagedephi(
    ctx: click.Context,
    override_rules: TextIO | None,
    verbose: int,
    quiet: int,
    log_file: Path,
    recursive: bool,
    profile: str,
) -> None:
    """Redact microscopy whole slide images."""
    obj = ImagedephiContext()
    # Store separately, to preserve the type of "obj"
    ctx.obj = obj

    if override_rules:
        obj.override_rule_set = Ruleset.parse_obj(yaml.safe_load(override_rules))
    if verbose or quiet or log_file:
        set_logging_config(verbose, quiet, log_file)


@imagedephi.command
@global_options
@click.argument("input-path", type=click.Path(exists=True, readable=True, path_type=Path))
@click.option(
    "-o",
    "--output-dir",
    default=Path.cwd(),
    show_default="current working directory",
    help="Path where output directory will be created.",
    type=click.Path(exists=True, file_okay=False, readable=True, writable=True, path_type=Path),
)
@click.option("--rename/--skip-rename", default=True)
@click.pass_obj
def run(
    obj: ImagedephiContext,
    input_path: Path,
    output_dir: Path,
    rename: bool,
    recursive,
    profile: str,
    verbose,
    quiet,
    log_file,
):
    """Perform the redaction of images."""
    if verbose or quiet or log_file:
        set_logging_config(verbose, quiet, log_file)
    redact_images(
        input_path,
        output_dir,
        obj.override_rule_set,
        rename,
        recursive=recursive,
        profile=profile,
    )


@imagedephi.command
@global_options
@click.argument("input-path", type=click.Path(exists=True, readable=True, path_type=Path))
@click.pass_obj
def plan(
    obj: ImagedephiContext, input_path: Path, recursive, profile, quiet, verbose, log_file
) -> None:
    """Print the redaction plan for images."""
    # Even if the user doesn't use the verbose flag, ensure logging level is set to
    # show info output of this command.
    v = verbose if verbose else 1
    set_logging_config(v, quiet, log_file)
    show_redaction_plan(input_path, obj.override_rule_set, recursive, profile)


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
