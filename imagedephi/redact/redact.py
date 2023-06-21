from __future__ import annotations

from collections.abc import Generator
import datetime
import importlib.resources
from pathlib import Path

import click
import tifftools
import tifftools.constants
import yaml

from imagedephi.rules import Ruleset

from .build_redaction_plan import FILE_EXTENSION_MAP, build_redaction_plan
from .svs import MalformedAperioFileError
from .tiff import UnsupportedFileTypeError


def _get_output_path(
    file_path: Path,
    output_dir: Path,
    base_name: str,
    count: int,
    max: int,
) -> Path:
    return output_dir / f"{base_name}_{count:0{len(str(max))}}{file_path.suffix}"


def get_base_rules():
    base_rules_path = importlib.resources.files("imagedephi") / "base_rules.yaml"
    with base_rules_path.open() as base_rules_stream:
        base_rule_set = Ruleset.parse_obj(yaml.safe_load(base_rules_stream))
        return base_rule_set


def iter_image_files(directory: Path) -> Generator[Path, None, None]:
    """
    Given a directory return an iterable of available images.

    May raise a PermissionError if the directory is not readable.
    """
    for child in directory.iterdir():
        if child.suffix in FILE_EXTENSION_MAP:
            yield child


def create_redact_dir(base_output_dir: Path) -> Path:
    """Given a directory, create and return a timestamped sub-directory within it."""
    time_stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    redact_dir = base_output_dir / f"Redacted_{time_stamp}"

    redact_dir.mkdir(parents=True)

    click.echo(f"Created redaction folder: {redact_dir}")
    return redact_dir


def redact_images(
    input_path: Path,
    output_dir: Path,
    override_rules: Ruleset | None = None,
    overwrite: bool = False,
) -> None:
    base_rules = get_base_rules()
    output_file_name_base = (
        override_rules.output_file_name if override_rules else base_rules.output_file_name
    )
    # Convert to a list in order to get the length
    images_to_redact = list(iter_image_files(input_path) if input_path.is_dir() else [input_path])
    output_file_counter = 1
    output_file_max = len(images_to_redact)
    redact_dir = create_redact_dir(output_dir)
    for image_file in images_to_redact:
        if image_file.suffix not in FILE_EXTENSION_MAP:
            click.echo(f"Image format for {image_file.name} not supported. Skipping...")
            continue
        try:
            redaction_plan = build_redaction_plan(image_file, base_rules, override_rules)
        except tifftools.TifftoolsError:
            click.echo(f"Could not open {image_file.name} as a tiff. Skipping...")
            continue
        except MalformedAperioFileError:
            click.echo(
                f"{image_file.name} could not be processed as a valid Aperio file. Skipping..."
            )
            continue
        except UnsupportedFileTypeError as e:
            click.echo(f"{image_file.name} could not be processed. {e.args[0]}")
            continue
        click.echo(f"Redacting {image_file.name}...")
        if not redaction_plan.is_comprehensive():
            click.echo(f"Redaction could not be performed for {image_file.name}.")
            redaction_plan.report_missing_rules()
        else:
            redaction_plan.execute_plan()
            output_path = _get_output_path(
                image_file,
                redact_dir,
                output_file_name_base,
                output_file_counter,
                output_file_max,
            )
            redaction_plan.save(output_path, overwrite)
            output_file_counter += 1


def show_redaction_plan(input_path: Path, override_rules: Ruleset | None = None) -> None:
    image_paths = iter_image_files(input_path) if input_path.is_dir() else [input_path]
    base_rules = get_base_rules()
    for image_path in image_paths:
        if image_path.suffix not in FILE_EXTENSION_MAP:
            click.echo(f"Image format for {image_path.name} not supported.", err=True)
            continue
        try:
            redaction_plan = build_redaction_plan(image_path, base_rules, override_rules)
        except tifftools.TifftoolsError:
            click.echo(f"Could not open {image_path.name} as a tiff.", err=True)
            continue
        except MalformedAperioFileError:
            click.echo(
                f"{image_path.name} could not be processed as a valid Aperio file.", err=True
            )
            continue
        except UnsupportedFileTypeError as e:
            click.echo(f"{image_path.name} could not be processed. {e.args[0]}")
            continue
        print(f"\nRedaction plan for {image_path.name}")
        redaction_plan.report_plan()
