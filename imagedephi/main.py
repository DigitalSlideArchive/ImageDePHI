from __future__ import annotations

from pathlib import Path

import click

from imagedephi.redact import redact_images


@click.group
def imagedephi():
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
