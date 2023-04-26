from __future__ import annotations

from collections.abc import Generator
import datetime
import importlib.resources
from pathlib import Path
from typing import TYPE_CHECKING

import click
import tifftools
import tifftools.constants
import yaml

from imagedephi.rules import RuleSet, RuleSource, build_ruleset

from .redaction_plan import FILE_EXTENSION_MAP
from .svs import MalformedAperioFileError
from .tiff import TiffBasedMetadataRedactionPlan

if TYPE_CHECKING:
    from tifftools.tifftools import TiffInfo


def _get_output_path(file_path: Path, output_dir: Path) -> Path:
    return output_dir / f"REDACTED_{file_path.name}"


def _save_redacted_tiff(tiff_info: TiffInfo, output_path: Path):
    tifftools.write_tiff(tiff_info, output_path, allowExisting=True)


def get_base_rules():
    base_rules_path = importlib.resources.files("imagedephi") / "base_rules.yaml"
    with base_rules_path.open() as base_rules_stream:
        base_rule_set = build_ruleset(yaml.safe_load(base_rules_stream), RuleSource.BASE)
        return base_rule_set


def iter_image_files(directory: Path) -> Generator[Path, None, None]:
    """
    Given a directory return an iterable of available images.

    May raise a PermissionError if the directory is not readable.
    """
    for child in directory.iterdir():
        if child.suffix in FILE_EXTENSION_MAP:
            yield child


def redact_images(
    input_path: Path,
    output_dir: Path,
    override_rules: RuleSet | None = None,
) -> None:
    base_rules = get_base_rules()
    images_to_redact = iter_image_files(input_path) if input_path.is_dir() else [input_path]
    time_stamp = datetime.datetime.now().isoformat(timespec="seconds")
    redact_dir = Path(f"{output_dir}/Redacted_{time_stamp}")
    try:
        redact_dir.mkdir(parents=True)
    except PermissionError:
        "Cannnot create an output directory, permission error."
    click.echo(f"Created redaction folder: {redact_dir}")
    for image_file in images_to_redact:
        if image_file.suffix not in FILE_EXTENSION_MAP:
            click.echo(f"Image format for {image_file.name} not supported. Skipping...")
            continue
        try:
            redaction_plan = TiffBasedMetadataRedactionPlan.build(
                image_file, base_rules, override_rules
            )
        except tifftools.TifftoolsError:
            click.echo(f"Could not open {image_file.name} as a tiff. Skipping...")
            continue
        except MalformedAperioFileError:
            click.echo(
                f"{image_file.name} could not be processed as a valid Aperio file. Skipping..."
            )
            continue
        click.echo(f"Redacting {image_file.name}...")
        if not redaction_plan.is_comprehensive():
            click.echo(f"Redaction could not be performed for {image_file.name}.")
            redaction_plan.report_missing_rules()
        else:
            redaction_plan.execute_plan()
            output_path = _get_output_path(image_file, redact_dir)
            _save_redacted_tiff(redaction_plan.get_image_data(), output_path)


def show_redaction_plan(input_path: Path, override_rules: RuleSet | None = None) -> None:
    image_paths = iter_image_files(input_path) if input_path.is_dir() else [input_path]
    for image_path in image_paths:
        if image_path.suffix not in FILE_EXTENSION_MAP:
            click.echo(f"Image format for {image_path.name} not supported.", err=True)
            continue
        base_rules = get_base_rules()
        try:
            metadata_redaction_plan = TiffBasedMetadataRedactionPlan.build(
                image_path, base_rules, override_rules
            )
        except tifftools.TifftoolsError:
            click.echo(f"Could not open {image_path.name} as a tiff.", err=True)
            continue
        except MalformedAperioFileError:
            click.echo(
                f"{image_path.name} could not be processed as a valid Aperio file.", err=True
            )
            continue
        print(f"\nRedaction plan for {image_path.name}")
        metadata_redaction_plan.report_plan()
