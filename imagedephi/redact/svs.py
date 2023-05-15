from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import tifftools
import tifftools.constants

from imagedephi.rules import ConcreteMetadataRule, FileFormat, SvsRules

from .tiff import TiffRedactionPlan

if TYPE_CHECKING:
    from tifftools.tifftools import IFD


class SvsDescription:
    prefix: str
    metadata: dict[str, str]

    def __init__(self, svs_description_string: str):
        description_components = svs_description_string.split("|")
        self.prefix = description_components[0]

        self.metadata = {}
        for metadata_component in description_components[1:]:
            key, value = [token.strip() for token in metadata_component.split("=")]
            self.metadata[key] = value

    def __str__(self) -> str:
        components = [self.prefix]
        components = components + [
            " = ".join([key, self.metadata[key]]) for key in self.metadata.keys()
        ]
        return "|".join(components)


class MalformedAperioFileError(Exception):
    """Raised when the program cannot process an Aperio/SVS file as expected."""

    ...


class SvsRedactionPlan(TiffRedactionPlan):
    """
    Represents a plan of action for redacting files in Aperio (.svs) format.

    Redaction for this type of file is similar to redaction for .tiff files, as the
    formats are similar. However, Aperio images store additional information in its
    ImageDescription tags. As a result, this tag is treated specially here.
    """

    file_format = FileFormat.SVS
    description_redaction_steps: dict[str, ConcreteMetadataRule]
    no_match_description_keys: set[str]
    rules: SvsRules

    def __init__(
        self,
        image_path: Path,
        rules: SvsRules,
    ) -> None:
        self.rules = rules
        self.image_redaction_steps = {}
        self.description_redaction_steps = {}
        super().__init__(image_path, rules)

        image_description_tag = tifftools.constants.Tag["ImageDescription"]
        if image_description_tag.value not in self.metadata_redaction_steps:
            raise MalformedAperioFileError()
        del self.metadata_redaction_steps[image_description_tag.value]

        self.description_redaction_steps = {}
        self.no_match_description_keys = set()
        ifds = self.tiff_info["ifds"]
        for tag, ifd in self._iter_tiff_tag_entries(ifds):
            if tag.value != image_description_tag.value:
                continue

            svs_description = SvsDescription(str(ifd["tags"][tag.value]["data"]))

            for key in svs_description.metadata.keys():
                key_rule = rules.image_description.get(key, None)
                if key_rule and self.is_match(key_rule, key):
                    self.description_redaction_steps[key] = key_rule
                else:
                    self.no_match_description_keys.add(key)

    def get_associated_image_key_for_ifd(self, ifd: IFD):
        """Attempt to match an associated image with a rule. Fallback to default rule."""
        image_description = str(ifd["tags"][270]["data"])
        # we could do additional checks, like look for a macro based on dimensions
        for key in self.rules.associated_images:
            if key in image_description:
                return key
        return "default"

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
        for tag_value, rule in self.metadata_redaction_steps.items():
            print(f"Tiff Tag {tag_value} - {rule.key_name}: {rule.action}")
        for key_name, rule in self.description_redaction_steps.items():
            print(f"SVS Image Description - {key_name}: {rule.action}")
        self.report_missing_rules()
        print("Aperio (.svs) Associated Image Redaction Plan\n")
        match_counts = {}
        for _, image_rule in self.image_redaction_steps.items():
            if image_rule.key_name not in match_counts:
                match_counts[image_rule.key_name] = 1
            else:
                match_counts[image_rule.key_name] = match_counts[image_rule.key_name] + 1
        for key in match_counts:
            print(
                f"{match_counts[key]} image(s) match rule:"
                f" {key} - {self.rules.associated_images[key].action}"
            )

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

    def execute_plan(self, temp_dir: Path) -> None:
        ifds = self.tiff_info["ifds"]
        new_ifds = self._redact_associated_images(ifds, temp_dir)
        image_description_tag = tifftools.constants.Tag["ImageDescription"]
        for tag, ifd in self._iter_tiff_tag_entries(new_ifds):
            rule = self.metadata_redaction_steps.get(tag.value)
            if rule is not None:
                self.apply(rule, ifd)
            elif tag.value == image_description_tag.value:
                self._redact_svs_image_description(ifd)
        self.tiff_info["ifds"] = new_ifds
