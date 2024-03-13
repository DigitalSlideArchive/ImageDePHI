from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import tifftools
import tifftools.constants

from imagedephi.rules import (
    ConcreteMetadataRule,
    FileFormat,
    MetadataReplaceRule,
    RedactionOperation,
    SvsRules,
)
from imagedephi.utils.logger import logger

from .tiff import TiffRedactionPlan

if TYPE_CHECKING:
    from tifftools.tifftools import IFD


class SvsDescription:
    prefix: str
    metadata: dict[str, str | int | float]

    def try_get_numeric_value(self, value: str) -> str | int | float:
        """Given an ImageDescription value, return a number version of it if applicable."""
        try:
            int(value)
            return int(value)
        except ValueError:
            try:
                float(value)
                return float(value)
            except ValueError:
                return value

    def __init__(self, svs_description_string: str):
        description_components = svs_description_string.split("|")
        self.prefix = description_components[0]

        self.metadata = {}
        for metadata_component in description_components[1:]:
            key, value = [token.strip() for token in metadata_component.split("=")]
            self.metadata[key] = self.try_get_numeric_value(value)

    def __str__(self) -> str:
        components = [self.prefix]
        components = components + [
            " = ".join([key, str(self.metadata[key])]) for key in self.metadata.keys()
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

    def get_associated_image_key_for_ifd(self, ifd: IFD) -> str:
        """
        Given a associated image IFD, return its semantic type.

        An associated image IFD is one that contains non-tiled image data.

        This will return `"default`" if no semantics can be determined.
        """
        # Check image description, it may contain 'macro' or 'label'
        image_description_tag = tifftools.constants.Tag["ImageDescription"]
        if image_description_tag.value in ifd["tags"]:
            image_description = str(ifd["tags"][image_description_tag.value]["data"])
            for key in self.rules.associated_images:
                if key in image_description:
                    return key

        # Check NewSubFileType bitmask. 'macro' could be encoded here
        newsubfiletype_tag = tifftools.constants.Tag["NewSubfileType"]
        if newsubfiletype_tag.value in ifd["tags"]:
            newsubfiletype = ifd["tags"][newsubfiletype_tag.value]["data"][0]
            reduced_image_bit = tifftools.constants.NewSubfileType["ReducedImage"].value
            macro_bit = tifftools.constants.NewSubfileType["Macro"].value
            if newsubfiletype & reduced_image_bit and newsubfiletype & macro_bit:
                return "macro"
        return "default"

    def is_match(self, rule: ConcreteMetadataRule, data: tifftools.TiffTag | str) -> bool:
        if rule.action in ["keep", "delete", "replace", "check_type"]:
            if isinstance(data, tifftools.TiffTag):
                return super().is_match(rule, data)
            return rule.key_name == data
        return False

    def determine_redaction_operation(
        self, rule: ConcreteMetadataRule, data: SvsDescription | IFD
    ) -> RedactionOperation:
        if isinstance(data, SvsDescription):
            if rule.action == "check_type":
                value = data.metadata[rule.key_name]
                passes_check = self.passes_type_check(
                    value, rule.valid_data_types, rule.expected_count
                )
                return "keep" if passes_check else "delete"
            if rule.action in ["keep", "replace", "delete"]:
                return rule.action
        else:
            return super().determine_redaction_operation(rule, data)
        return "delete"

    def apply(self, rule: ConcreteMetadataRule, data: SvsDescription | IFD) -> None:
        if isinstance(data, SvsDescription):
            redaction_operation = self.determine_redaction_operation(rule, data)
            if redaction_operation == "delete":
                del data.metadata[rule.key_name]
            elif redaction_operation == "replace":
                assert isinstance(rule, MetadataReplaceRule)
                data.metadata[rule.key_name] = rule.new_value
            return
        return super().apply(rule, data)

    def is_comprehensive(self) -> bool:
        return super().is_comprehensive() and not self.no_match_description_keys

    def report_missing_rules(self, report) -> None:
        if self.is_comprehensive():
            logger.info("The redaction plan is comprehensive.")
        else:
            if self.no_match_tags:
                super().report_missing_rules(report)
            if self.no_match_description_keys:
                logger.error(
                    "The following keys were found in Aperio ImageDescription strings "
                    "and could not be redacted given the current set of rules."
                )
                for key in self.no_match_description_keys:
                    logger.error(f"Missing key (Aperio ImageDescription): {key}")
                    report[self.image_path.name]["missing_keys"].append(key)

    def report_plan(self) -> dict[str, dict[str, str]]:
        logger.info("Aperio (.svs) Metadata Redaction Plan\n")
        offset = -1
        ifd_count = 0
        report = {}
        report[self.image_path.name] = {}
        for tag, ifd in self._iter_tiff_tag_entries(self.tiff_info["ifds"]):
            if ifd["offset"] != offset:
                offset = ifd["offset"]
                ifd_count += 1
                logger.info(f"IFD {ifd_count}:")
            if tag.value == tifftools.constants.Tag["ImageDescription"]:
                image_description = SvsDescription(str(ifd["tags"][tag.value]["data"]))
                for key_name, _data in image_description.metadata.items():
                    rule = self.description_redaction_steps[key_name]
                    operation = self.determine_redaction_operation(rule, image_description)
                    logger.info(f"SVS Image Description - {key_name}: {operation}")
                    report[self.image_path.name][key_name] = operation
                continue
            rule = self.metadata_redaction_steps[tag.value]
            operation = self.determine_redaction_operation(rule, ifd)
            logger.info(f"Tiff Tag {tag.value} - {rule.key_name}: {operation}")
            report[self.image_path.name][rule.key_name] = operation
        self.report_missing_rules(report)
        logger.info("Aperio (.svs) Associated Image Redaction Plan\n")
        match_counts = {}
        for _, image_rule in self.image_redaction_steps.items():
            if image_rule.key_name not in match_counts:
                match_counts[image_rule.key_name] = 1
            else:
                match_counts[image_rule.key_name] = match_counts[image_rule.key_name] + 1
        for key in match_counts:
            logger.info(
                f"{match_counts[key]} image(s) match rule:"
                f" {key} - {self.rules.associated_images[key].action}"
            )
            report[self.image_path.name] = (
                f"{match_counts[key]} image(s) match rule:"
                f" {key} - {self.rules.associated_images[key].action}"
            )

        return report

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
        new_ifds = self._redact_associated_images(ifds)
        image_description_tag = tifftools.constants.Tag["ImageDescription"]
        for tag, ifd in self._iter_tiff_tag_entries(new_ifds):
            rule = self.metadata_redaction_steps.get(tag.value)
            if rule is not None:
                self.apply(rule, ifd)
            elif tag.value == image_description_tag.value:
                self._redact_svs_image_description(ifd)
        self.tiff_info["ifds"] = new_ifds
