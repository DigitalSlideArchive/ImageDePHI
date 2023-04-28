from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Type

import tifftools
import tifftools.constants

from imagedephi.models.rules import ConcreteMetadataRule, FileFormat, Ruleset
from imagedephi.utils.tiff import get_tiff_tag

from .redaction_plan import FILE_EXTENSION_MAP, RedactionPlan

if TYPE_CHECKING:
    from tifftools.tifftools import IFD, TiffInfo


class TiffBasedMetadataRedactionPlan(RedactionPlan):
    tiff_info: TiffInfo

    def __init__(self, tiff_info: TiffInfo, base_rules: Ruleset, override_rule_set: Ruleset | None):
        self.tiff_info = tiff_info

    @classmethod
    def get_all_subclasses(cls) -> Generator[Type[TiffBasedMetadataRedactionPlan], None, None]:
        for subclass in cls.__subclasses__():
            yield from subclass.get_all_subclasses()
            yield subclass

    @classmethod
    def build(
        cls, image_path: Path, base_rules: Ruleset, override_rules: Ruleset | None = None
    ) -> TiffBasedMetadataRedactionPlan:
        file_extension = FILE_EXTENSION_MAP[image_path.suffix]
        for redaction_plan_class in cls.get_all_subclasses():
            if file_extension == redaction_plan_class.file_format:
                tiff_info = tifftools.read_tiff(str(image_path))
                return redaction_plan_class(tiff_info, base_rules, override_rules)
        else:
            raise Exception(f"File format for {image_path} not supported.")

    def get_image_data(self) -> TiffInfo:
        return self.tiff_info


class TiffMetadataRedactionPlan(TiffBasedMetadataRedactionPlan):
    """
    Represents a plan of action for redacting metadata from TIFF images.

    The plan can be used for reporting to end users what steps will be made to redact their TIFF
    images, and also executing the plan.
    """

    file_format = FileFormat.TIFF
    tiff_info: TiffInfo
    redaction_steps: dict[int, ConcreteMetadataRule]
    no_match_tags: list[tifftools.TiffTag]

    @staticmethod
    def _iter_tiff_tag_entries(
        ifds: list[IFD],
        tag_set=tifftools.constants.Tag,
    ) -> Generator[tuple[tifftools.TiffTag, IFD], None, None]:
        for ifd in ifds:
            for tag_id, entry in sorted(ifd["tags"].items()):
                tag: tifftools.TiffTag = tifftools.constants.get_or_create_tag(
                    tag_id,
                    tagSet=tag_set,
                    datatype=tifftools.Datatype[entry["datatype"]],
                )
                if not tag.isIFD():
                    yield tag, ifd
                else:
                    # entry['ifds'] contains a list of lists
                    # see tifftools.read_tiff
                    for sub_ifds in entry.get("ifds", []):
                        yield from TiffMetadataRedactionPlan._iter_tiff_tag_entries(
                            sub_ifds, tag.get("tagset")
                        )

    def __init__(
        self,
        tiff_info: TiffInfo,
        base_rule_set: Ruleset,
        override_rule_set: Ruleset | None = None,
    ) -> None:
        self.tiff_info = tiff_info

        self.redaction_steps = {}
        self.no_match_tags = []
        ifds = self.tiff_info["ifds"]
        override_rules = (
            override_rule_set.get_format_rules(self.file_format).metadata
            if override_rule_set
            else None
        )
        base_rules: dict[str, ConcreteMetadataRule] = base_rule_set.get_format_rules(
            self.file_format
        ).metadata
        merged_rules = base_rules | override_rules if override_rules else base_rules
        for tag, _ in self._iter_tiff_tag_entries(ifds):
            tag_rule = None
            for name in [tag.name] + list(tag.get("altnames", set())):
                tag_rule = merged_rules.get(name, None)
                if tag_rule and self.is_match(tag_rule, tag):
                    self.redaction_steps[tag.value] = tag_rule
                    break
            else:
                self.no_match_tags.append(tag)

    def is_match(self, rule: ConcreteMetadataRule, tag: tifftools.TiffTag) -> bool:
        if rule.action in ["keep", "delete", "replace"]:
            rule_tag = get_tiff_tag(rule.key_name)
            return rule_tag.value == tag.value
        return False

    def apply(self, rule: ConcreteMetadataRule, ifd: IFD) -> None:
        tag = get_tiff_tag(rule.key_name)
        if rule.action == "delete":
            del ifd["tags"][tag.value]
        elif rule.action == "replace":
            ifd["tags"][tag.value]["data"] = rule.new_value

    def is_comprehensive(self) -> bool:
        return len(self.no_match_tags) == 0

    def report_missing_rules(self) -> None:
        if self.is_comprehensive():
            print("This redaction plan is comprehensive.")
        else:
            print("The following tags could not be redacted given the current set of rules.")
            for tag in self.no_match_tags:
                print(f"Missing tag (tiff): {tag.value} - {tag.name}")

    def report_plan(self) -> None:
        print("Tiff Metadata Redaction Plan\n")
        for tag_value, rule in self.redaction_steps.items():
            print(f"Tiff Tag {tag_value} - {rule.key_name}: {rule.action}")
        self.report_missing_rules()

    def execute_plan(self) -> None:
        """Modify the image data according to the redaction rules."""
        ifds = self.tiff_info["ifds"]
        for tag, ifd in self._iter_tiff_tag_entries(ifds):
            rule = self.redaction_steps.get(tag.value)
            if rule is not None:
                self.apply(rule, ifd)
