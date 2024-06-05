from __future__ import annotations

from collections.abc import Generator
from enum import Enum
from pathlib import Path
from uuid import uuid4

import pydicom
from pydicom import valuerep
from pydicom.datadict import keyword_for_tag
from pydicom.dataelem import DataElement
from pydicom.dataset import Dataset
from pydicom.tag import BaseTag

from imagedephi.rules import (
    ConcreteMetadataRule,
    DeleteRule,
    DicomRules,
    FileFormat,
    KeepRule,
    MetadataReplaceRule,
    RedactionOperation,
)
from imagedephi.utils.logger import logger

from .redaction_plan import RedactionPlan

VR_TO_DUMMY_VALUE: dict[str, str | float | int | list | bytes] = {}
for vr in valuerep.STR_VR:
    VR_TO_DUMMY_VALUE[vr] = ""
for vr in valuerep.FLOAT_VR:
    VR_TO_DUMMY_VALUE[vr] = 0.0
for vr in valuerep.INT_VR:
    VR_TO_DUMMY_VALUE[vr] = 0
for vr in valuerep.LIST_VR:
    VR_TO_DUMMY_VALUE[vr] = []
for vr in valuerep.BYTES_VR:
    VR_TO_DUMMY_VALUE[vr] = b""

VR_TO_EXPECTED_TYPE: dict[str, type] = {}
for vr in valuerep.STR_VR:
    VR_TO_EXPECTED_TYPE[vr] = str
for vr in valuerep.FLOAT_VR:
    VR_TO_EXPECTED_TYPE[vr] = float
for vr in valuerep.INT_VR:
    VR_TO_EXPECTED_TYPE[vr] = int
for vr in valuerep.LIST_VR:
    VR_TO_EXPECTED_TYPE[vr] = list
for vr in valuerep.BYTES_VR:
    VR_TO_EXPECTED_TYPE[vr] = bytes

WSI_IMAGE_TYPE_INDEX = 2


class WsiImageType(Enum):
    OVERVIEW = "OVERVIEW"
    VOLUME = "VOLUME"
    THUMBNAIL = "THUMBNAIL"
    LABEL = "LABEL"


class DicomRedactionPlan(RedactionPlan):
    """
    Represents a plan of action for redacting metadata from DICOM images.

    Each instance of this class works on a single .dcm file.
    """

    file_format = FileFormat.DICOM
    image_path: Path
    dicom_data: pydicom.FileDataset
    image_type: WsiImageType
    metadata_redaction_steps: dict[int, ConcreteMetadataRule]
    no_match_tags: list[BaseTag]
    uid_map: dict[str, str]

    @staticmethod
    def _iter_dicom_elements(
        dicom_dataset: Dataset,
    ) -> Generator[tuple[DataElement, Dataset], None, None]:
        for element in dicom_dataset:
            if element.VR == valuerep.VR.SQ:
                for dataset in element.value:
                    yield from DicomRedactionPlan._iter_dicom_elements(dataset)
                # Treat the sequence as its own element as well.
                # Some of the rules generated from the DICOM docs
                # include rules for sequences.
                # Return the sequence after to protect against deletion while looping.
                yield element, dicom_dataset
            else:
                yield element, dicom_dataset

    def __init__(self, image_path: Path, rules: DicomRules, uid_map: dict[str, str] | None) -> None:
        self.image_path = image_path
        self.dicom_data = pydicom.dcmread(image_path)
        self.image_type = WsiImageType(self.dicom_data.ImageType[WSI_IMAGE_TYPE_INDEX])

        self.metadata_redaction_steps = {}
        self.no_match_tags = []

        # Determine what, if any, action to take with this file's
        # image data. Currently only matters for label and overview
        # images.
        self.associated_image_rule = rules.associated_images.get(
            self.image_type.value.lower(), None
        )

        # When redacting many files at a time, keep track of all UIDs across all files,
        # since the DICOM format uses separate files for different resolutions and
        # associated images.
        self.uid_map = uid_map if uid_map else {}

        for element, _ in DicomRedactionPlan._iter_dicom_elements(self.dicom_data):
            custom_metadata_key = "CustomMetadataItem"
            keyword = keyword_for_tag(element.tag)
            # Check keyword and (gggg,eeee) representation
            tag_in_rules = keyword in rules.metadata or str(element.tag) in rules.metadata
            if not tag_in_rules:
                if element.tag.group % 2 == 1:
                    if rules.delete_custom_metadata:
                        # If the group is odd, it is custom metadata. Use the custom metadata action
                        self.metadata_redaction_steps[element.tag] = DeleteRule(
                            key_name=custom_metadata_key, action="delete"
                        )
                    else:
                        self.metadata_redaction_steps[element.tag] = KeepRule(
                            key_name=custom_metadata_key, action="keep"
                        )
                else:
                    self.no_match_tags.append(element.tag)
                continue

            rule = rules.metadata[keyword]
            if rule.action in [
                "keep",
                "delete",
                "replace",
                "check_type",
                "empty",
                "replace_uid",
                "replace_dummy",
            ]:
                self.metadata_redaction_steps[element.tag] = rule
            else:
                self.no_match_tags.append(element.tag)
                continue

    def passes_type_check(self, element: DataElement) -> bool:
        return isinstance(element.value, VR_TO_EXPECTED_TYPE[element.VR])

    def determine_redaction_operation(
        self, rule: ConcreteMetadataRule, element: DataElement
    ) -> RedactionOperation:
        if rule.action == "check_type":
            return "keep" if self.passes_type_check(element) else "delete"
        if rule.action in ["keep", "delete", "replace", "replace_uid", "replace_dummy", "empty"]:
            return rule.action
        return "delete"

    def report_plan(self) -> dict[str, dict[str | int, str | int]]:
        logger.info("DICOM Metadata Redaction Plan\n")
        if self.associated_image_rule:
            if self.associated_image_rule.action == "delete":
                logger.info(
                    f"This image is a DICOM {self.image_type.value}."
                    "This file will not be written to the output directory."
                )
                return {}
        report: dict[str, dict[str | int, str | int]] = {}
        report[self.image_path.name] = {}
        for element, _ in DicomRedactionPlan._iter_dicom_elements(self.dicom_data):
            rule = self.metadata_redaction_steps.get(element.tag, None)
            if rule:
                operation = self.determine_redaction_operation(rule, element)
                logger.info(f"DICOM Tag {element.tag} - {rule.key_name}: {operation}")
                report[self.image_path.name][f"{element.tag}_{rule.key_name}"] = operation
        self.report_missing_rules(report)
        return report

    def apply(self, rule: ConcreteMetadataRule, element: DataElement, dataset: Dataset):
        operation = self.determine_redaction_operation(rule, element)
        if operation == "delete":
            # TODO make sure this works as expected, we are modifying a dataset
            # while looping through it
            del dataset[element.tag]
        elif operation == "replace":
            assert isinstance(rule, MetadataReplaceRule)
            element.value = rule.new_value
        elif operation == "empty":
            element.value = None
        elif operation == "replace_uid":
            if element.value not in self.uid_map:
                new_uid = "2.25." + str(uuid4().int)
                self.uid_map[element.value] = str(new_uid)
            element.value = self.uid_map[element.value]
        elif operation == "replace_dummy":
            element.value = VR_TO_DUMMY_VALUE[element.VR]

    def execute_plan(self) -> None:
        if self.associated_image_rule:
            if self.associated_image_rule.action != "delete":
                raise NotImplementedError(
                    "Only 'delete' is supported for associated DICOM images at this time."
                )
        for element, dataset in DicomRedactionPlan._iter_dicom_elements(self.dicom_data):
            rule = self.metadata_redaction_steps[element.tag]
            if rule is not None:
                self.apply(rule, element, dataset)

    def is_comprehensive(self) -> bool:
        return not self.no_match_tags

    def report_missing_rules(self, report=None) -> None:
        if self.is_comprehensive():
            logger.info("The redaction plan is comprehensive.")
        else:
            logger.error("The following tags could not be redacted given the current set of rules.")
            if report is not None:
                report[self.image_path.name]["missing_tags"] = []

            for tag in self.no_match_tags:
                logger.error(f"Missing tag (dicom): {tag} - {keyword_for_tag(tag)}")
                if report is not None:
                    report[self.image_path.name]["missing_tags"].append({tag: keyword_for_tag(tag)})

    def save(self, output_path: Path, overwrite: bool) -> None:
        if self.associated_image_rule and self.associated_image_rule.action == "delete":
            # Don't write this file to the output directory if it is marked to be deleted
            return
        if output_path.exists():
            if overwrite:
                logger.info(f"Found existing redaction for {self.image_path.name}. Overwriting...")
            else:
                logger.warn(
                    f"Could not redact {self.image_path.name}, existing redacted file in output "
                    "directory. Use the --overwrite-existing-output flag to overwrite previously "
                    "redacted fiels."
                )
                return
        self.dicom_data.save_as(output_path)
