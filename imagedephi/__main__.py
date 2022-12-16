from pathlib import Path

import click

from . import redact_images


@click.command()
@click.argument(
    "input-dir", type=click.Path(exists=True, file_okay=False, readable=True, path_type=Path)
)
@click.argument(
    "output-dir", type=click.Path(exists=True, file_okay=False, writable=True, path_type=Path)
)
def main(input_dir: Path, output_dir: Path) -> None:
    """Redact microscopy whole slide images."""
    redact_images(input_dir, output_dir)
    click.echo("Done!")


if __name__ == "__main__":
    main()
