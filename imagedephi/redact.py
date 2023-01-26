from __future__ import annotations

from collections.abc import Generator
import importlib.resources
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING

import click
import tifftools
import tifftools.constants
import yaml

from imagedephi.rules import MetadataTiffRule, RuleSet, RuleSource, build_ruleset

if TYPE_CHECKING:
    from tifftools.tifftools import IFD, TiffInfo


class TiffMetadataRedactionPlan:
    """
    Represents a plan of action for redacting metadata from TIFF images.

    The plan can be used for reporting to end users what steps will be made to redact their TIFF
    images, and also executing the plan.
    """

    tiff_info: TiffInfo
    redaction_steps: dict[int, MetadataTiffRule]
    no_match_tags: list[tifftools.TiffTag]

    @staticmethod
    def _iter_tiff_tag_entries(
        ifds: list[IFD],
    ) -> Generator[tuple[tifftools.TiffTag, IFD], None, None]:
        for ifd in ifds:
            for tag_id, entry in sorted(ifd["tags"].items()):
                tag: tifftools.TiffTag = tifftools.constants.get_or_create_tag(
                    tag_id, datatype=tifftools.Datatype[entry["datatype"]]
                )
                if not tag.isIFD():
                    yield tag, ifd
                else:
                    # entry['ifds'] contains a list of lists
                    # see tifftools.read_tiff
                    for sub_ifds in entry.get("ifds", []):
                        yield from TiffMetadataRedactionPlan._iter_tiff_tag_entries(sub_ifds)

    def __init__(
        self,
        tiff_info: TiffInfo,
        base_rules: list[MetadataTiffRule],
        override_rules: list[MetadataTiffRule],
    ) -> None:
        self.tiff_info = tiff_info

        self.redaction_steps = {}
        self.no_match_tags = []
        ifds = self.tiff_info["ifds"]
        for tag, _ in self._iter_tiff_tag_entries(ifds):
            # First iterate through overrides, then base
            for rule in chain(override_rules, base_rules):
                if rule.is_match(tag):
                    self.redaction_steps[tag.value] = rule
                    break
            else:
                # End of iteration, without "break"; no matching rule found anywhere
                self.no_match_tags.append(tag)

    def report_missing_rules(self) -> None:
        if self.no_match_tags:
            click.echo("The following tags could not be redacted given the current set of rules.")
            for tag in self.no_match_tags:
                click.echo(f"{tag.value} - {tag.name}")
        else:
            click.echo("This redaction plan is comprehensive.")

    def report_plan(self) -> None:
        click.echo("Tiff Metadata Redaction Plan\n")
        for rule in self.redaction_steps.values():
            click.echo(rule.get_description())
        self.report_missing_rules()

    def execute_plan(self) -> None:
        """Modify the image data according to the redaction rules."""
        ifds = self.tiff_info["ifds"]
        for tag, ifd in self._iter_tiff_tag_entries(ifds):
            rule = self.redaction_steps.get(tag.value)
            if rule is not None:
                rule.apply(ifd)


def _get_output_path(file_path: Path, output_dir: Path) -> Path:
    return output_dir / f"REDACTED_{file_path.name}"


def _save_redacted_tiff(tiff_info: TiffInfo, output_path: Path, input_path: Path, overwrite: bool):
    if overwrite or not output_path.exists():
        if output_path.exists():
            click.echo(f"Found existing redaction for {input_path.name}. Overwriting...")
        tifftools.write_tiff(tiff_info, output_path, allowExisting=True)
    else:
        click.echo(
            f"Could not redact {input_path.name}, existing redacted file in output directory. "
            "Use the --overwrite-existing-output flag to overwrite previously redacted files."
        )


def get_base_rules():
    base_rules_path = importlib.resources.files("imagedephi") / "base_rules.yaml"
    with base_rules_path.open() as base_rules_stream:
        base_rule_set = build_ruleset(yaml.safe_load(base_rules_stream), RuleSource.BASE)
        return base_rule_set


def redact_images(
    image_dir: Path,
    output_dir: Path,
    override_rules: RuleSet | None = None,
    overwrite: bool = False,
) -> None:
    base_rules = get_base_rules()
    for child in image_dir.iterdir():
        try:
            tiff_info: TiffInfo = tifftools.read_tiff(child)
        except tifftools.TifftoolsError:
            click.echo(f"Could not open {child.name} as a tiff. Skipping...")
            continue
        click.echo(f"Redacting {child.name}...")
        redaction_plan = TiffMetadataRedactionPlan(
            tiff_info,
            base_rules.get_metadata_tiff_rules(),
            override_rules.get_metadata_tiff_rules() if override_rules else [],
        )
        if redaction_plan.no_match_tags:
            click.echo(f"Redaction could not be performed for {child.name}.")
            redaction_plan.report_missing_rules()
        else:
            redaction_plan.execute_plan()
            output_path = _get_output_path(child, output_dir)
            _save_redacted_tiff(tiff_info, output_path, child, overwrite)


def show_redaction_plan(image_path: click.Path, override_rules: RuleSet | None = None):
    base_rules = get_base_rules()
    tiff_info = tifftools.read_tiff(str(image_path))
    redaction_plan = TiffMetadataRedactionPlan(
        tiff_info,
        base_rules.get_metadata_tiff_rules(),
        override_rules.get_metadata_tiff_rules() if override_rules else [],
    )
    redaction_plan.report_plan()
