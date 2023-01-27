from __future__ import annotations

from collections.abc import Generator
import importlib.resources
from pathlib import Path
from typing import TYPE_CHECKING

import click
import tifftools
import tifftools.constants
import yaml

from imagedephi.rules import RuleSet, RuleSource, TiffMetadataRule, build_ruleset

if TYPE_CHECKING:
    from tifftools.tifftools import IFD, TiffInfo


class TiffMetadataRedactionPlan:
    """
    Represents a plan of action for redacting metadata from TIFF images.

    The plan can be used for reporting to end users what steps will be made to redact their TIFF
    images, and also executing the plan.
    """

    redaction_steps: dict[int, TiffMetadataRule]
    no_match_tags: list[tifftools.TiffTag]
    image_data: TiffInfo
    base_rules: list[TiffMetadataRule]
    override_rules: list[TiffMetadataRule]

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

    def _add_tag_to_plan(self, tag: tifftools.TiffTag) -> None:
        """Determine how to handle a given tag."""
        for rule in self.override_rules:
            if rule.is_match(tag):
                self.redaction_steps[tag.value] = rule
                return
        for rule in self.base_rules:
            if rule.is_match(tag):
                self.redaction_steps[tag.value] = rule
                return
        self.no_match_tags.append(tag)

    def __init__(
        self,
        tiff_info: TiffInfo,
        base_rules: list[TiffMetadataRule],
        override_rules: list[TiffMetadataRule],
    ) -> None:
        self.redaction_steps = {}
        self.no_match_tags = []
        self.image_data = tiff_info
        self.base_rules = base_rules
        self.override_rules = override_rules
        ifds = self.image_data["ifds"]
        for tag, _ in self._iter_tiff_tag_entries(ifds):
            self._add_tag_to_plan(tag)

    def report_missing_rules(self) -> None:
        if len(self.no_match_tags) == 0:
            click.echo("This redaction plan is comprehensive.")
        else:
            click.echo("The following tags could not be redacted given the current set of rules.")
            for tag in self.no_match_tags:
                click.echo(f"{tag.value} - {tag.name}")

    def report_plan(self) -> None:
        click.echo("Tiff Metadata Redaction Plan\n")
        for _key, rule in self.redaction_steps.items():
            click.echo(rule.get_description())
        self.report_missing_rules()

    def _redact_one_tag(self, ifd: IFD, tag: tifftools.TiffTag) -> None:
        if tag.value in self.redaction_steps:
            rule = self.redaction_steps[tag.value]
            rule.apply(ifd)

    def execute_plan(self) -> None:
        """Modify the image data according to the redaction rules."""
        ifds = self.image_data["ifds"]
        for tag, ifd in self._iter_tiff_tag_entries(ifds):
            self._redact_one_tag(ifd, tag)


def _get_output_path(file_path: Path, output_dir: Path) -> Path:
    return output_dir / f"REDACTED_{file_path.name}"


def get_base_rules():
    base_rules_path = importlib.resources.files("imagedephi") / "base_rules.yaml"
    with base_rules_path.open() as base_rules_stream:
        base_rule_set = build_ruleset(yaml.safe_load(base_rules_stream), RuleSource.BASE)
        return base_rule_set


def redact_images(image_dir: Path, output_dir: Path, override_rules: RuleSet | None = None) -> None:
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
            base_rules.get_tiff_metadata_rules(),
            override_rules.get_tiff_metadata_rules() if override_rules else [],
        )
        if len(redaction_plan.no_match_tags):
            click.echo(f"Redaction could not be performed for {child.name}.")
            redaction_plan.report_missing_rules()
        else:
            redaction_plan.execute_plan()
            output_path = _get_output_path(child, output_dir)
            tifftools.write_tiff(tiff_info, output_path)


def show_redaction_plan(image_path: click.Path, override_rules: RuleSet | None = None):
    base_rules = get_base_rules()
    tiff_info = tifftools.read_tiff(str(image_path))
    redaction_plan = TiffMetadataRedactionPlan(
        tiff_info,
        base_rules.get_tiff_metadata_rules(),
        override_rules.get_tiff_metadata_rules() if override_rules else [],
    )
    redaction_plan.report_plan()
