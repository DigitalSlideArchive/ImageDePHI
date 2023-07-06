from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image, TiffTags
from PIL.TiffImagePlugin import ImageFileDirectory_v2
import tifftools
import tifftools.constants

from imagedephi.rules import (
    ConcreteImageRule,
    ConcreteMetadataRule,
    FileFormat,
    ImageReplaceRule,
    MetadataReplaceRule,
    RedactionOperation,
    TiffRules,
)
from imagedephi.utils.tiff import get_tiff_tag

from .redaction_plan import RedactionPlan

if TYPE_CHECKING:
    from tifftools.tifftools import IFD, TiffInfo


class UnsupportedFileTypeError(Exception):
    """Thrown when a file can be opened by tifftools but not redacted."""


class TiffRedactionPlan(RedactionPlan):
    """
    Represents a plan of action for redacting metadata from TIFF images.

    The plan can be used for reporting to end users what steps will be made to redact their TIFF
    images, and also executing the plan.
    """

    file_format = FileFormat.TIFF
    image_path: Path
    tiff_info: TiffInfo
    metadata_redaction_steps: dict[int, ConcreteMetadataRule]
    image_redaction_steps: dict[int, ConcreteImageRule]
    no_match_tags: list[tifftools.TiffTag]

    @staticmethod
    def is_tiled(ifd: IFD):
        """Determine if an IFD represents a tiled image."""
        return tifftools.Tag.TileWidth.value in ifd["tags"]

    @staticmethod
    def _iter_ifds(
        ifds: list[IFD],
        tag_set=tifftools.constants.Tag,
    ) -> Generator[IFD, None, None]:
        for ifd in ifds:
            for tag_id, entry in ifd["tags"].items():
                tag: tifftools.TiffTag = tifftools.constants.get_or_create_tag(
                    tag_id,
                    tagSet=tag_set,
                    datatype=tifftools.Datatype[entry["datatype"]],
                )
                if tag.isIFD():
                    # entry['ifds'] contains a list of lists
                    # see tifftools.read_tiff
                    for sub_ifds in entry.get("ifds", []):
                        yield from TiffRedactionPlan._iter_ifds(sub_ifds, tag.get("tagset"))
            yield ifd

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
                        yield from TiffRedactionPlan._iter_tiff_tag_entries(
                            sub_ifds, tag.get("tagset")
                        )

    def get_associated_image_key_for_ifd(self, ifd: IFD) -> str:
        """
        Given a associated image IFD, return its semantic type.

        For TIFF files, this will always return `"default`".
        """
        return "default"

    def __init__(
        self,
        image_path: Path,
        rules: TiffRules,
    ) -> None:
        self.image_path = image_path
        self.tiff_info = tifftools.read_tiff(str(image_path))

        self.metadata_redaction_steps = {}
        self.image_redaction_steps = {}
        self.no_match_tags = []
        ifds = self.tiff_info["ifds"]

        for tag, _ifd in self._iter_tiff_tag_entries(ifds):
            if tag.value == tifftools.constants.Tag["ImageJMetadata"].value:
                raise UnsupportedFileTypeError("Redaction for ImageJ files is not supported")
            if tag.value == tifftools.constants.Tag["NDPI_FORMAT_FLAG"].value:
                raise UnsupportedFileTypeError("Redaction for NDPI files is not supported")
            tag_rule = None
            for name in [tag.name] + list(tag.get("altnames", set())):
                tag_rule = rules.metadata.get(name, None)
                if tag_rule and self.is_match(tag_rule, tag):
                    self.metadata_redaction_steps[tag.value] = tag_rule
                    break
            else:
                self.no_match_tags.append(tag)

        for ifd in self._iter_ifds(ifds):
            if not self.is_tiled(ifd):
                associated_image_key = self.get_associated_image_key_for_ifd(ifd)
                # IFD offset is a useful unique identifier for the IFD itself
                self.image_redaction_steps[ifd["offset"]] = rules.associated_images[
                    associated_image_key
                ]

    def is_match(self, rule: ConcreteMetadataRule, tag: tifftools.TiffTag) -> bool:
        if rule.action in ["keep", "delete", "replace", "check_type"]:
            rule_tag = get_tiff_tag(rule.key_name)
            return rule_tag.value == tag.value
        return False

    def passes_type_check(self, metadata_value: Any, valid_types: tuple[type], expected_count: int) -> bool:
        passes_check = False
        if isinstance(metadata_value, list):
            return len(metadata_value) == expected_count and all(
                isinstance(item, valid_types) for item in metadata_value
            )
        else:
            return isinstance(metadata_value, valid_types)


    def determine_redaction_action(
        self, rule: ConcreteMetadataRule, ifd: IFD
    ) -> RedactionOperation:
        """
        Given a rule and the IFD it applies to, return the actual action.

        The "check_type" rules will either delete or do nothing to the metadata.
        This function is used to determine which action will be applied, and is
        useful for reporting.
        """
        if rule.action == "check_type":
            tag = get_tiff_tag(rule.key_name)
            value = ifd["tags"][tag.value]["data"]
            valid_types = tuple(rule.valid_data_type)
            expected_count = 2 * rule.expected_count if rule.expected_type == "rational" else rule.expected_count
            passes_check = self.passes_type_check(value, valid_types, expected_count)
            return "keep" if passes_check else "delete"
        if rule.action in ["keep", "replace", "delete"]:
            return rule.action
        return "delete"

    def apply(self, rule: ConcreteMetadataRule, ifd: IFD) -> None:
        tag = get_tiff_tag(rule.key_name)
        operation = self.determine_redaction_action(rule, ifd)
        if operation == "delete":
            del ifd["tags"][tag.value]
        elif operation == "replace":
            assert isinstance(rule, MetadataReplaceRule)
            ifd["tags"][tag.value]["data"] = rule.new_value

    def is_comprehensive(self) -> bool:
        return not self.no_match_tags

    def report_missing_rules(self) -> None:
        if self.is_comprehensive():
            print("This redaction plan is comprehensive.")
        else:
            print("The following tags could not be redacted given the current set of rules.")
            for tag in self.no_match_tags:
                print(f"Missing tag (tiff): {tag.value} - {tag.name}")

    def report_plan(self) -> None:
        print("Tiff Metadata Redaction Plan\n")
        offset = -1
        ifd_count = 0
        for tag, ifd in self._iter_tiff_tag_entries(self.tiff_info["ifds"]):
            if ifd["offset"] != offset:
                offset = ifd["offset"]
                ifd_count += 1
                print(f"IFD {ifd_count}:")
            rule = self.metadata_redaction_steps[tag.value]
            print(f"Tiff Tag {tag.value} - {rule.key_name}: {rule.action}")
        self.report_missing_rules()
        print("Tiff Associated Image Redaction Plan\n")
        print(f"Found {len(self.image_redaction_steps)} associated images")
        if self.image_redaction_steps:
            default_rule = list(self.image_redaction_steps.values())[0]
            print(f"Redaction action: {default_rule.action}")

    def create_new_image(self, ifd: IFD, rule: ImageReplaceRule) -> BytesIO:
        """
        Given an IFD with an image, return a redacted IFD, serialized in a byte stream.

        If `rule` is `"blank_image"`, this redacted IFD contains a blank image and all
        ASCII TIFF entries from the original IFD.
        """
        image = None
        if rule.replace_with == "blank_image":
            # Create blank image with the same size
            image_width_tag = tifftools.constants.Tag["ImageWidth"]
            image_height_tag = tifftools.constants.Tag["ImageHeight"]
            width = int(ifd["tags"][image_width_tag.value]["data"][0])
            length = int(ifd["tags"][image_height_tag.value]["data"][0])
            image = Image.new("RGB", (width, length))

            # Copy all ASCII entries to a new IFD.
            # Only copy ASCII to avoid copying entries that affect the image decoding (even those
            # that PIL doesn't itself write; e.g. orientation or ICC color profile).
            new_ifd = ImageFileDirectory_v2()
            for tag_value, entry in ifd["tags"].items():
                if entry["datatype"] == tifftools.constants.Datatype.ASCII:
                    new_ifd[tag_value] = entry["data"]
                    new_ifd.tagtype[tag_value] = TiffTags.ASCII

            # Encode the new IFD, including the new blank image within it
            new_ifd_stream = BytesIO()
            image.save(new_ifd_stream, "TIFF", compression="jpeg", tiffinfo=new_ifd)
            return new_ifd_stream

        raise Exception("Redaction option not currently supported")

    def replace_associated_image(self, ifds: list[IFD], index: int, rule: ImageReplaceRule):
        old_ifd = ifds[index]
        new_ifd_stream = self.create_new_image(old_ifd, rule)
        replacement_tiff_info = tifftools.read_tiff(new_ifd_stream)
        new_ifd = replacement_tiff_info["ifds"][0]
        ifds[index] = new_ifd

    def _redact_associated_images(
        self, ifds: list[IFD], tag_set=tifftools.constants.Tag
    ) -> list[IFD]:
        delete_ifd_indices = []
        for index, ifd in enumerate(ifds):
            for tag_id, entry in ifd["tags"].items():
                tag = tifftools.constants.get_or_create_tag(
                    tag_id, tagSet=tag_set, datatype=tifftools.Datatype[entry["datatype"]]
                )
                if tag.isIFD():
                    sub_ifds_list = entry.get("ifds", [])
                    for idx, sub_ifds in enumerate(sub_ifds_list):
                        sub_ifds_list[idx] = self._redact_associated_images(
                            sub_ifds, tag.get("tagset")
                        )
            if ifd["offset"] in self.image_redaction_steps:
                rule = self.image_redaction_steps[ifd["offset"]]
                if rule.action == "delete":
                    delete_ifd_indices.append(index)
                elif rule.action == "replace":
                    self.replace_associated_image(ifds, index, rule)
        return [ifd for idx, ifd in enumerate(ifds) if idx not in delete_ifd_indices]

    def execute_plan(self) -> None:
        """Modify the image data according to the redaction rules."""
        ifds = self.tiff_info["ifds"]
        new_ifds = self._redact_associated_images(ifds)
        for tag, ifd in self._iter_tiff_tag_entries(new_ifds):
            rule = self.metadata_redaction_steps.get(tag.value)
            if rule is not None:
                self.apply(rule, ifd)
        self.tiff_info["ifds"] = new_ifds

    def save(self, output_path: Path, overwrite: bool) -> None:
        if output_path.exists():
            if overwrite:
                print(f"Found existing redaction for {self.image_path.name}. Overwriting...")
            else:
                print(
                    f"Could not redact {self.image_path.name}, existing redacted file in output "
                    "directory. Use the --overwrite-existing-output flag to overwrite previously "
                    "redacted files."
                )
                return
        tifftools.write_tiff(self.tiff_info, output_path, allowExisting=True)
