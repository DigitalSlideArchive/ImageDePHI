from __future__ import annotations

import abc
from collections.abc import Generator
import importlib.resources
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING

import click
import tifftools
import tifftools.constants
import yaml

from imagedephi.rules import (
    FileFormat,
    MetadataSvsRule,
    MetadataTiffRule,
    RuleSet,
    RuleSource,
    SvsDescription,
    build_ruleset,
)

if TYPE_CHECKING:
    from tifftools.tifftools import IFD, TiffInfo


class RedactionPlan:
    file_format: FileFormat

    @abc.abstractmethod
    def report_plan(self):
        ...

    @abc.abstractmethod
    def execute_plan(self):
        ...


class MetadataRedactionPlan(RedactionPlan):
    @classmethod
    def build(
        cls, image_path: Path, base_rules: RuleSet, override_rules: RuleSet | None = None
    ) -> MetadataRedactionPlan:
        file_extension = image_path.suffix
        file_extension_map: dict[str, FileFormat] = {
            ".tif": FileFormat.TIFF,
            ".tiff": FileFormat.TIFF,
            ".svs": FileFormat.SVS,
        }
        if file_extension_map[file_extension] == FileFormat.TIFF:
            tiff_info = tifftools.read_tiff(str(image_path))
            return TiffMetadataRedactionPlan(
                tiff_info,
                base_rules.get_metadata_tiff_rules(),
                override_rules.get_metadata_tiff_rules() if override_rules else [],
            )
        if file_extension_map[file_extension] == FileFormat.SVS:
            tiff_info = tifftools.read_tiff(str(image_path))
            return SvsMetadataRedactionPlan(
                tiff_info,
                base_rules.get_metadata_tiff_rules(),
                base_rules.get_metadata_svs_rules(),
                override_rules.get_metadata_tiff_rules() if override_rules else [],
                override_rules.get_metadata_svs_rules() if override_rules else [],
            )
        raise Exception(f"File format for {image_path} not supported.")


class TiffMetadataRedactionPlan(MetadataRedactionPlan):
    """
    Represents a plan of action for redacting metadata from TIFF images.

    The plan can be used for reporting to end users what steps will be made to redact their TIFF
    images, and also executing the plan.
    """

    file_format = FileFormat.TIFF
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


class SvsMetadataRedactionPlan(TiffMetadataRedactionPlan):
    """
    Represents a plan of action for redacting files in Aperio (.svs) format.

    Redaction for this type of file is similar to redaction for .tiff files, as the
    formats are similar. However, Aperio images store additional information in its
    ImageDescription tags. As a result, this tag is treated specially here.
    """

    file_format = FileFormat.SVS
    description_redaction_steps: dict[str, MetadataSvsRule]
    no_match_description_keys: list[str]

    def __init__(
        self,
        tiff_info: TiffInfo,
        base_rules_tiff: list[MetadataTiffRule],
        base_rules_svs: list[MetadataSvsRule],
        override_rules_tiff: list[MetadataTiffRule],
        override_rules_svs: list[MetadataSvsRule],
    ):
        super().__init__(tiff_info, base_rules_tiff, override_rules_tiff)

        image_description_tag = tifftools.constants.Tag["ImageDescription"]
        del self.redaction_steps[image_description_tag.value]

        self.description_redaction_steps = {}
        self.no_match_description_keys = []
        ifds = self.tiff_info["ifds"]
        for tag, ifd in self._iter_tiff_tag_entries(ifds):
            if tag.value != image_description_tag.value:
                continue

            svs_description = SvsDescription(str(ifd["tags"][tag.value]["data"]))
            for key in svs_description.metadata.keys():
                for rule in chain(override_rules_svs, base_rules_svs):
                    if rule.is_match(key):
                        self.description_redaction_steps[key] = rule
                        break
                else:
                    self.no_match_description_keys.append(key)

    def report_missing_rules(self) -> None:
        is_comprehensive = True
        if self.no_match_tags:
            is_comprehensive = False
            click.echo("The following tags could not be redacted given the current set of rules.")
            for tag in self.no_match_tags:
                click.echo(f"{tag.value} - {tag.name}")
        if self.no_match_description_keys:
            is_comprehensive = False
            click.echo(
                "The following keys were found in Aperio ImageDescription strings "
                "and could not be redacted given the current set of rules."
            )
            for key in self.no_match_description_keys:
                click.echo(key)
        if is_comprehensive:
            click.echo("The redaction plan is comprehensive.")

    def report_plan(self) -> None:
        click.echo("Aperio (.svs) Metadata Redaction Plan\n")
        for rule in chain(self.redaction_steps.values(), self.description_redaction_steps.values()):
            click.echo(rule.get_description())
        self.report_missing_rules()


def _get_output_path(file_path: Path, output_dir: Path) -> Path:
    return output_dir / f"REDACTED_{file_path.name}"


def _save_redacted_tiff(tiff_info: TiffInfo, output_path: Path, input_path: Path, overwrite: bool):
    if output_path.exists():
        if overwrite:
            click.echo(f"Found existing redaction for {input_path.name}. Overwriting...")
        else:
            click.echo(
                f"Could not redact {input_path.name}, existing redacted file in output directory. "
                "Use the --overwrite-existing-output flag to overwrite previously redacted files."
            )
            return
    tifftools.write_tiff(tiff_info, output_path, allowExisting=True)


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


def show_redaction_plan(image_path: Path, override_rules: RuleSet | None = None):
    base_rules = get_base_rules()
    metadata_redaction_plan = MetadataRedactionPlan.build(image_path, base_rules, override_rules)
    metadata_redaction_plan.report_plan()
