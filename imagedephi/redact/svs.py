from __future__ import annotations

from itertools import chain
from typing import TYPE_CHECKING

import tifftools
import tifftools.constants

from imagedephi.rules import FileFormat, MetadataSvsRule, RuleSet, SvsDescription

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
    description_redaction_steps: dict[str, MetadataSvsRule]
    no_match_description_keys: set[str]

    def __init__(
        self,
        tiff_info: TiffInfo,
        base_rule_set: RuleSet,
        override_rule_set: RuleSet | None = None,
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
                override_rule_set.get_metadata_svs_rules() if override_rule_set else []
            )
            base_svs_rules = base_rule_set.get_metadata_svs_rules()
            for key in svs_description.metadata.keys():
                for rule in chain(override_svs_rules, base_svs_rules):
                    if rule.is_match(key):
                        self.description_redaction_steps[key] = rule
                        break
                else:
                    self.no_match_description_keys.add(key)

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
        for rule in chain(self.redaction_steps.values(), self.description_redaction_steps.values()):
            print(rule.get_description())
        self.report_missing_rules()

    def _redact_svs_image_description(self, ifd: IFD) -> None:
        image_description_tag = tifftools.constants.Tag["ImageDescription"]
        image_description = SvsDescription(str(ifd["tags"][image_description_tag.value]["data"]))

        # We may be modifying the dictionary as we iterate over its keys,
        # hence the need for a list
        for key in list(image_description.metadata.keys()):
            rule = self.description_redaction_steps.get(key)
            if rule is not None:
                rule.apply(image_description)
        ifd["tags"][image_description_tag.value]["data"] = str(image_description)

    def execute_plan(self) -> None:
        ifds = self.tiff_info["ifds"]
        image_description_tag = tifftools.constants.Tag["ImageDescription"]
        for tag, ifd in self._iter_tiff_tag_entries(ifds):
            rule = self.redaction_steps.get(tag.value)
            if rule is not None:
                rule.apply(ifd)
            elif tag.value == image_description_tag.value:
                self._redact_svs_image_description(ifd)
