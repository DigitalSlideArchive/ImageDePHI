from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
import tifftools
import tifftools.constants

from .rules import (
    RedactMethod,
    RuleFormat,
    RuleSet,
    RuleSource,
    RuleType,
    TiffMetadataRule,
    make_rule,
)

if TYPE_CHECKING:
    from tifftools.tifftools import IFD, TiffInfo


class TiffMetadataRedactionPlan:
    """
    Represents a plan of action for redacting metadata from TIFF images.

    The plan can be used for reporting to end users what steps will be made to redact their TIFF
    images, and also executing the plan.
    """

    redaction_steps: dict[int, tuple[TiffMetadataRule, RuleSource]]
    no_match_tags: list[tifftools.TiffTag]
    image_data: TiffInfo
    base_rules: list[TiffMetadataRule]
    override_rules: list[TiffMetadataRule]

    def __add_tag_to_plan(self, tag: tifftools.Tag):
        """Determine how to handle a given tag."""

        for rule in self.override_rules:
            if rule.is_match(tag):
                self.redaction_steps[tag.value] = (rule, RuleSource.OVERRIDE)
                return
        for rule in self.base_rules:
            if rule.is_match(tag):
                self.redaction_steps[tag.value] = (rule, RuleSource.BASE)
                return
        self.no_match_tags.append(tag)

    def __build_redaction_steps(self, ifds: list[IFD]) -> None:
        for ifd in ifds:
            for tag_id, tag_info in sorted(ifd["tags"].items()):
                tag: tifftools.TiffTag = tifftools.constants.get_or_create_tag(
                    tag_id,
                    datatype=tifftools.Datatype[tag_info["datatype"]],
                )
                if not tag.isIFD():
                    self.__add_tag_to_plan(tifftools.constants.Tag[tag_id])
                else:
                    # tag_info['ifds'] contains a list of lists
                    # see tifftools.read_tiff
                    for sub_ifds in tag_info.get("ifds", []):
                        self.__build_redaction_steps(sub_ifds)

    def __init__(self, base_rules: RuleSet, override_rules: RuleSet, tiff_info: TiffInfo):
        self.redaction_steps = {}
        self.no_match_tags = []
        self.image_data = tiff_info
        self.base_rules = [
            rule for rule in base_rules.rules[RuleFormat.TIFF] if isinstance(rule, TiffMetadataRule)
        ]
        self.override_rules = [
            rule
            for rule in override_rules.rules[RuleFormat.TIFF]
            if isinstance(rule, TiffMetadataRule)
        ]
        self.__build_redaction_steps(self.image_data["ifds"])

    def report_plan(self):
        click.echo("Tiff Metadata Redaction Plan\n")
        for key in self.redaction_steps:
            rule = self.redaction_steps[key][0]
            source = "Base" if self.redaction_steps[key][1] == RuleSource.BASE else "Override"
            tag = tifftools.constants.Tag[key]
            click.echo(f"Tag {tag.value} - {tag.name}: {rule.redact_method} ({source})")
        if len(self.no_match_tags) > 0:
            click.echo("The following tags could not be redacted given the current set of rules.")
            for tag in self.no_match_tags:
                click.echo(f"{tag.value} - {tag.name}")

    def __redact_one_tag(self, ifd: IFD, tag: tifftools.Tag):
        rule, _ = self.redaction_steps.get(tag.value, None)
        if rule:
            rule.apply(ifd)

    def __redact_image(self, ifds: list[IFD]):
        for ifd in ifds:
            for tag_id, tag_info in sorted(ifd["tags"].items()):
                tag: tifftools.TiffTag = tifftools.constants.get_or_create_tag(
                    tag_id, datatype=tifftools.Datatype[tag_info["datatype"]]
                )
                if not tag.isIFD():
                    self.__redact_one_tag(ifd, tag)
                else:
                    for sub_ifds in tag_info.get("ifds", []):
                        self.__redact_image(sub_ifds)

    def execute_plan(self):
        """Modify the image data according to the redaction rules."""
        ifds = self.image_data["ifds"]
        self.__redact_image(ifds)


def build_ruleset(rules_dict: dict) -> RuleSet:
    """Read in metadata redaction rules from a file."""
    rule_set_rules = {}
    for file_format in rules_dict["rules"]:
        format_key = RuleFormat[file_format.upper()]
        format_rules = rules_dict["rules"][file_format]
        format_rule_objects = []
        for rule in format_rules:
            rule_type = RuleType[rule["type"].upper()]
            format_rule_objects.append(make_rule(format_key, rule_type, rule))
        rule_set_rules[format_key] = format_rule_objects
    return RuleSet(rules_dict["name"], rules_dict["description"], rule_set_rules)


def get_tags_to_redact() -> dict[int, dict[str, Any]]:
    return {
        270: {
            "id": 270,
            "name": "ImageDescription",
            "method": RedactMethod.REPLACE,
            "replace_value": "Redacted by ImageDePHI",
        }
    }


def redact_one_tag(ifd: IFD, tag: tifftools.TiffTag, redact_instructions: dict[str, Any]) -> None:
    if redact_instructions["method"] == RedactMethod.REPLACE:
        ifd["tags"][tag.value]["data"] = redact_instructions["replace_value"]
    elif redact_instructions["method"] == RedactMethod.DELETE:
        del ifd["tags"][tag.value]


def redact_tiff_tags(ifds: list[IFD], tags_to_redact: dict[int, dict[str, Any]]) -> None:
    for ifd in ifds:
        for tag_id, tag_info in sorted(ifd["tags"].items()):
            tag: tifftools.TiffTag = tifftools.constants.get_or_create_tag(
                tag_id,
                datatype=tifftools.Datatype[tag_info["datatype"]],
            )
            if not tag.isIFD():
                if tag.value in tags_to_redact:
                    redact_one_tag(ifd, tag, tags_to_redact[tag.value])
            else:
                # tag_info['ifds'] contains a list of lists
                # see tifftools.read_tiff
                for sub_ifds in tag_info.get("ifds", []):
                    redact_tiff_tags(sub_ifds, tags_to_redact)


def redact_one_image(tiff_info: TiffInfo, output_path: Path) -> None:
    ifds = tiff_info["ifds"]
    tags_to_redact = get_tags_to_redact()
    redact_tiff_tags(ifds, tags_to_redact)
    tifftools.write_tiff(tiff_info, output_path)


def get_output_path(file_path: Path, output_dir: Path) -> Path:
    return output_dir / f"REDACTED_{file_path.name}"


def redact_images(image_dir: Path, output_dir: Path) -> None:
    for child in image_dir.iterdir():
        try:
            tiff_info: TiffInfo = tifftools.read_tiff(child)
        except tifftools.TifftoolsError:
            click.echo(f"Could not open {child.name} as a tiff. Skipping...")
            continue
        click.echo(f"Redacting {child.name}...")
        redact_one_image(tiff_info, get_output_path(child, output_dir))


def redact_images_using_rules(
    image_dir: Path, output_dir: Path, base_rules: RuleSet, override_rules: RuleSet
) -> None:
    for child in image_dir.iterdir():
        try:
            tiff_info: TiffInfo = tifftools.read_tiff(child)
        except tifftools.TifftoolsError:
            click.echo(f"Could not open {child.name} as a tiff. Skipping...")
            continue
        click.echo(f"Redacting {child.name}...")
        redaction_plan = TiffMetadataRedactionPlan(base_rules, override_rules, tiff_info)
        redaction_plan.execute_plan()
        output_path = get_output_path(child, output_dir)
        tifftools.write_tiff(tiff_info, output_path)


def show_redaction_plan(image_path: click.Path, base_rules: RuleSet, override_rules: RuleSet):
    tiff_info = tifftools.read_tiff(image_path)
    redaction_plan = TiffMetadataRedactionPlan(base_rules, override_rules, tiff_info)
    redaction_plan.report_plan()
