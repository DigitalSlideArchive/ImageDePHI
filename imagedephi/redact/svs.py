from __future__ import annotations

from typing import TYPE_CHECKING

import tifftools
import tifftools.constants

from imagedephi.models.rules import ConcreteMetadataRule, Ruleset
from imagedephi.rules import FileFormat, SvsDescription

from .tiff import TiffMetadataRedactionPlan

if TYPE_CHECKING:
    from tifftools.tifftools import IFD, TiffInfo


class MalformedAperioFileError(Exception):
    """Raised when the program cannot process an Aperio/SVS file as expected."""

    ...


class SvsMetadataRedactionPlan(TiffMetadataRedactionPlan):
    """
    Represents a plan of action for redacting files in Aperio (.svs) format.

    Redaction for this type of file is similar to redaction for .tiff files, as the
    formats are similar. However, Aperio images store additional information in its
    ImageDescription tags. As a result, this tag is treated specially here.
    """

    file_format = FileFormat.SVS
    description_redaction_steps: dict[str, ConcreteMetadataRule]
    no_match_description_keys: set[str]

    def __init__(
        self,
        tiff_info: TiffInfo,
        base_rule_set: Ruleset,
        override_rule_set: Ruleset | None = None,
    ) -> None:
        super().__init__(tiff_info, base_rule_set, override_rule_set)

        image_description_tag = tifftools.constants.Tag["ImageDescription"]
        if image_description_tag.value not in self.redaction_steps:
            raise MalformedAperioFileError()
        del self.redaction_steps[image_description_tag.value]

        self.description_redaction_steps = {}
        self.no_match_description_keys = set()
        ifds = self.tiff_info["ifds"]
        for tag, ifd in self._iter_tiff_tag_entries(ifds):
            if tag.value != image_description_tag.value:
                continue

            svs_description = SvsDescription(str(ifd["tags"][tag.value]["data"]))
            override_svs_rules = (
                override_rule_set.svs.image_description if override_rule_set else None
            )
            base_svs_rules = base_rule_set.svs.image_description
            merged_svs_rules = (
                base_svs_rules | override_svs_rules if override_svs_rules else base_svs_rules
            )

            for key in svs_description.metadata.keys():
                key_rule = merged_svs_rules.get(key, None)
                if key_rule and self.is_match(key_rule, key):
                    self.description_redaction_steps[key] = key_rule
                else:
                    self.no_match_description_keys.add(key)

    def is_match(self, rule: ConcreteMetadataRule, data: tifftools.TiffTag | str) -> bool:
        if rule.action in ["keep", "delete", "replace"]:
            if isinstance(data, tifftools.TiffTag):
                return super().is_match(rule, data)
            return rule.key_name == data
        return False

    def apply(self, rule: ConcreteMetadataRule, data: SvsDescription | IFD) -> None:
        if isinstance(data, SvsDescription):
            if rule.action == "delete":
                del data.metadata[rule.key_name]
            elif rule.action == "replace":
                data.metadata[rule.key_name] = rule.new_value
            return
        return super().apply(rule, data)

    def is_comprehensive(self) -> bool:
        return super().is_comprehensive() and not self.no_match_description_keys

    def report_missing_rules(self) -> None:
        if self.is_comprehensive():
            print("The redaction plan is comprehensive.")
        else:
            if self.no_match_tags:
                super().report_missing_rules()
            if self.no_match_description_keys:
                print(
                    "The following keys were found in Aperio ImageDescription strings "
                    "and could not be redacted given the current set of rules."
                )
                for key in self.no_match_description_keys:
                    print(f"Missing key (Aperio ImageDescription): {key}")

    def report_plan(self) -> None:
        print("Aperio (.svs) Metadata Redaction Plan\n")
        for tag_value, rule in self.redaction_steps.items():
            print(f"Tiff Tag {tag_value} - {rule.key_name}: {rule.action}")
        for key_name, rule in self.description_redaction_steps.items():
            print(f"SVS Image Description - {key_name}: {rule.action}")
        self.report_missing_rules()

    def _redact_svs_image_description(self, ifd: IFD) -> None:
        image_description_tag = tifftools.constants.Tag["ImageDescription"]
        image_description = SvsDescription(str(ifd["tags"][image_description_tag.value]["data"]))

        # We may be modifying the dictionary as we iterate over its keys,
        # hence the need for a list
        for key in list(image_description.metadata.keys()):
            rule = self.description_redaction_steps.get(key)
            if rule is not None:
                self.apply(rule, image_description)
        ifd["tags"][image_description_tag.value]["data"] = str(image_description)

    def execute_plan(self) -> None:
        ifds = self.tiff_info["ifds"]
        image_description_tag = tifftools.constants.Tag["ImageDescription"]
        for tag, ifd in self._iter_tiff_tag_entries(ifds):
            rule = self.redaction_steps.get(tag.value)
            if rule is not None:
                self.apply(rule, ifd)
            elif tag.value == image_description_tag.value:
                self._redact_svs_image_description(ifd)
