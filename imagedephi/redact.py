from __future__ import annotations

from collections.abc import Generator
import importlib.resources
from pathlib import Path
from typing import TYPE_CHECKING

import click
import tifftools
import tifftools.constants
import yaml

from imagedephi.rules import RuleFormat, RuleSet, RuleSource, RuleType, TiffMetadataRule, make_rule

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
                self.redaction_steps[tag.value] = (rule, RuleSource.OVERRIDE)
                return
        for rule in self.base_rules:
            if rule.is_match(tag):
                self.redaction_steps[tag.value] = (rule, RuleSource.BASE)
                return
        self.no_match_tags.append(tag)

    def _build_redaction_steps(self, ifds: list[IFD]) -> None:
        for tag, _ in self._iter_tiff_tag_entries(ifds):
            self._add_tag_to_plan(tag)

    def __init__(
        self, tiff_info: TiffInfo, base_rules: RuleSet, override_rules: RuleSet | None
    ) -> None:
        self.redaction_steps = {}
        self.no_match_tags = []
        self.image_data = tiff_info
        self.base_rules = [
            rule for rule in base_rules.rules[RuleFormat.TIFF] if isinstance(rule, TiffMetadataRule)
        ]
        if override_rules is None:
            self.override_rules = []
        else:
            self.override_rules = [
                rule
                for rule in override_rules.rules[RuleFormat.TIFF]
                if isinstance(rule, TiffMetadataRule)
            ]
        self._build_redaction_steps(self.image_data["ifds"])

    def report_missing_rules(self) -> None:
        if len(self.no_match_tags) == 0:
            click.echo("This redaction plan is comprehensive.")
        else:
            click.echo("The following tags could not be redacted given the current set of rules.")
            for tag in self.no_match_tags:
                click.echo(f"{tag.value} - {tag.name}")

    def report_plan(self) -> None:
        click.echo("Tiff Metadata Redaction Plan\n")
        for key, (rule, rule_source) in self.redaction_steps.items():
            source = "Base" if rule_source == RuleSource.BASE else "Override"
            # What if tifftools can't find the tag
            tag = tifftools.constants.Tag[key]
            # Use rule title if it exists
            click.echo(f"Tag {tag.value} - {tag.name}: {rule.redact_method} ({source})")
        self.report_missing_rules()

    def _redact_one_tag(self, ifd: IFD, tag: tifftools.TiffTag) -> None:
        if tag.value in self.redaction_steps:
            rule = self.redaction_steps[tag.value][0]
            rule.apply(ifd)

    def _redact_image(self, ifds: list[IFD]) -> None:
        for tag, ifd in self._iter_tiff_tag_entries(ifds):
            self._redact_one_tag(ifd, tag)

    def execute_plan(self) -> None:
        """Modify the image data according to the redaction rules."""
        ifds = self.image_data["ifds"]
        self._redact_image(ifds)


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


def _get_output_path(file_path: Path, output_dir: Path) -> Path:
    return output_dir / f"REDACTED_{file_path.name}"


def get_base_rules():
    base_rules_path = importlib.resources.files("imagedephi") / "base_rules.yaml"
    with base_rules_path.open() as base_rules_stream:
        base_rule_set = build_ruleset(yaml.safe_load(base_rules_stream))
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
        redaction_plan = TiffMetadataRedactionPlan(tiff_info, base_rules, override_rules)
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
    redaction_plan = TiffMetadataRedactionPlan(tiff_info, base_rules, override_rules)
    redaction_plan.report_plan()
