from __future__ import annotations

import asyncio
import csv
import importlib.resources
import logging
from pathlib import Path
import sys
import webbrowser

import click
from hypercorn import Config
from hypercorn.asyncio import serve
import pooch
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
import yaml

from imagedephi.gui.app import app
from imagedephi.redact import ProfileChoice, redact_images, show_redaction_plan
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
        "-R",
        "--override-rules",
        type=click.Path(exists=True, readable=True, path_type=Path),
        help="User-defined rules to override defaults.",
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
    click.option(
        "-r", "--recursive", is_flag=True, help="Apply the command to images in subdirectories"
    ),
]


def global_options(func):
    for option in _global_options:
        func = option(func)
    return func


def _check_parent_params(ctx, profile, override_rules, recursive, quiet, verbose, log_file):
    params = {
        "override_rules": (
            ctx.parent.params["override_rules"]
            if ctx.parent.params["override_rules"]
            else override_rules
        ),
        "profile": (
            ctx.parent.params["profile"] if ctx.parent.params["profile"] != "default" else profile
        ),
        "recursive": (
            ctx.parent.params["recursive"] if ctx.parent.params["recursive"] else recursive
        ),
        "quiet": ctx.parent.params["quiet"] if ctx.parent.params["quiet"] else quiet,
        "verbose": ctx.parent.params["verbose"] if ctx.parent.params["verbose"] else verbose,
        "log_file": ctx.parent.params["log_file"] if ctx.parent.params["log_file"] else log_file,
    }
    return params


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
@global_options
def imagedephi(
    verbose: int,
    quiet: int,
    log_file: Path,
    override_rules: Path | None,
    profile: str,
    recursive: bool,
) -> None:
    """Redact microscopy whole slide images."""
    if verbose or quiet or log_file:
        set_logging_config(verbose, quiet, log_file)


@imagedephi.command(no_args_is_help=True)
@global_options
@click.argument(
    "input-path",
    type=click.Path(exists=True, readable=True, path_type=Path),
    required=False
)
@click.option("-i", "--index", default=1, help="Starting index of the images to redact.", type=int)
@click.option(
    "-c",
    "--command-file",
    type=click.Path(exists=True, readable=True, path_type=Path),
    help="File containing redaction command. "
    "[INPUT_PATH] must be provided as an argument or in the command file.",
)
@click.option(
    "-o",
    "--output-dir",
    default=Path.cwd(),
    show_default="current working directory",
    help="Path where output directory will be created.",
    type=click.Path(exists=True, file_okay=False, readable=True, writable=True, path_type=Path),
)
@click.option("--rename/--skip-rename", default=True)
@click.pass_context
def run(
    ctx,
    input_path: Path,
    output_dir: Path,
    override_rules: Path | None,
    profile: str,
    recursive: bool,
    rename: bool,
    quiet,
    verbose,
    log_file,
    index,
    command_file: Path,
):
    """Perform the redaction of images."""
    params = _check_parent_params(ctx, profile, override_rules, recursive, quiet, verbose, log_file)
    if params["verbose"] or params["quiet"] or params["log_file"]:
        set_logging_config(params["verbose"], params["quiet"], params["log_file"])
    command_params = {}
    if command_file:
        with command_file.open() as f:
            command_params = yaml.safe_load(f)
            command_input = command_params["input_path"]
            if input_path is None and command_params.get("input_path") is None:
                raise click.BadParameter(
                    "Input path must be provided either in the command file or as an argument."
                )
    redact_images(
        input_path or Path(command_input),
        output_dir or command_params.get("output_dir"),
        override_rules=params["override_rules"] or command_params.get("override_rules"),
        rename=rename if "rename" not in command_params else command_params["rename"],
        recursive=params["recursive"] if "recursive" not in command_params else command_params["recursive"],
        profile=params["profile"] if "profile" not in command_params else command_params["profile"],
        index=index if "index" not in command_params else command_params["index"],
    )


@imagedephi.command(no_args_is_help=True)
@global_options
@click.argument("input-path", type=click.Path(exists=True, readable=True, path_type=Path))
@click.pass_context
def plan(
    ctx,
    input_path: Path,
    profile: str,
    override_rules: Path | None,
    recursive: bool,
    quiet,
    verbose,
    log_file,
) -> None:
    """Print the redaction plan for images."""
    params = _check_parent_params(ctx, profile, override_rules, recursive, quiet, verbose, log_file)

    # Even if the user doesn't use the verbose flag, ensure logging level is set to
    # show info output of this command.
    v = params["verbose"] if params["verbose"] else 1
    set_logging_config(v, params["quiet"], params["log_file"])
    show_redaction_plan(
        input_path,
        override_rules=params["override_rules"],
        recursive=params["recursive"],
        profile=params["profile"],
    )


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


@imagedephi.command
@click.option(
    "--data-dir",
    type=click.Path(file_okay=False, readable=True, writable=True, path_type=Path),
    default=Path.cwd(),
    help="Location where demo data will be downloaded.",
)
def demo_data(data_dir: Path):
    """Download data for the Image DePHI demo to the specified directory."""
    try:
        demo_file_dir = data_dir / "demo_files"
        demo_file_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.error("Cannot create demo data directory, permission error")
        raise
    demo_file_manifest = importlib.resources.files("imagedephi") / "demo_files.csv"
    with demo_file_manifest.open() as fd:
        reader = csv.DictReader(fd)
        rows = [row for row in reader]
        logger.info(f"Downloading files to {demo_file_dir}")
        with logging_redirect_tqdm(loggers=[logger]):
            for row in tqdm(rows, desc="Downloading demo images...", position=0, leave=True):
                file_name = row["file_name"]
                hash = row["hash"]
                algo, hash_val = hash.split(":")
                pooch.retrieve(
                    url=f"https://data.kitware.com/api/v1/file/hashsum/{algo}/{hash_val}/download",
                    known_hash=hash,
                    fname=file_name,
                    path=demo_file_dir,
                )
