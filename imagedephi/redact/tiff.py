from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING
import uuid

from PIL import Image
import tifftools
import tifftools.constants

from imagedephi.rules import (
    ConcreteImageRule,
    ConcreteMetadataRule,
    FileFormat,
    ReplaceImageRule,
    TiffRules,
)
from imagedephi.utils.tiff import get_tiff_tag

from .redaction_plan import RedactionPlan

if TYPE_CHECKING:
    from tifftools.tifftools import IFD, TagEntry, TiffInfo


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
        tile_width_tag = tifftools.constants.get_or_create_tag("TileWidth", tifftools.constants.Tag)
        return tile_width_tag.value in ifd["tags"]

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
                if not tag.isIFD():
                    yield ifd
                else:
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

    def get_associated_image_key_for_ifd(self, ifd: IFD):
        """Use only the default rule if a more specific format can't be determined."""
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

        for tag, _ in self._iter_tiff_tag_entries(ifds):
            tag_rule = None
            for name in [tag.name] + list(tag.get("altnames", set())):
                tag_rule = rules.metadata.get(name, None)
                if tag_rule and self.is_match(tag_rule, tag):
                    self.metadata_redaction_steps[tag.value] = tag_rule
                    break
            else:
                self.no_match_tags.append(tag)

        for ifd in TiffRedactionPlan._iter_ifds(ifds):
            if not TiffRedactionPlan.is_tiled(ifd):
                associated_image_key = self.get_associated_image_key_for_ifd(ifd)
                self.image_redaction_steps[ifd["offset"]] = rules.associated_images[
                    associated_image_key
                ]

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
        for tag_value, rule in self.metadata_redaction_steps.items():
            print(f"Tiff Tag {tag_value} - {rule.key_name}: {rule.action}")
        self.report_missing_rules()
        print("Tiff Associated Image Redaction Plan\n")
        print(f"Found {len(self.image_redaction_steps)} associated images")
        if len(self.image_redaction_steps):
            default_rule = list(self.image_redaction_steps.values())[0]
            print(f"Redaction action: {default_rule.action}")

    def create_new_image(self, ifd: IFD, rule: ReplaceImageRule, temp_dir: Path) -> Path:
        image = None
        if rule.replace_with == "blank_image":
            width = int(ifd["tags"][256]["data"][0])
            length = int(ifd["tags"][257]["data"][0])
            output_path = temp_dir / str(uuid.uuid4())
            image = Image.new("RGB", (width, length))
            image.save(output_path, "TIFF", compression="jpeg")
            return output_path
        raise Exception("Redaction option not currently supported")

    def update_new_ifd(self, old_ifd: IFD, new_ifd: IFD) -> None:
        for tag_value, entry in old_ifd["tags"].items():
            if tag_value not in new_ifd["tags"].keys():
                new_entry: TagEntry = {
                    "datatype": entry["datatype"],
                    "count": entry["count"],
                    "data": entry["data"],
                }
                new_ifd["tags"][tag_value] = new_entry

    def replace_associated_image(
        self, ifds: list[IFD], index: int, rule: ReplaceImageRule, temp_dir: Path
    ):
        old_ifd = ifds[index]
        new_image_path = self.create_new_image(old_ifd, rule, temp_dir)
        replacement_tiff_info = tifftools.read_tiff(new_image_path)
        new_ifd = replacement_tiff_info["ifds"][0]
        self.update_new_ifd(old_ifd, new_ifd)
        ifds[index] = new_ifd

    def _redact_associated_images(
        self, ifds: list[IFD], temp_dir: Path, tag_set=tifftools.constants.Tag
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
                            sub_ifds, temp_dir, tag.get("tagset")
                        )
            if ifd["offset"] in self.image_redaction_steps:
                rule = self.image_redaction_steps[ifd["offset"]]
                if rule.action == "delete":
                    delete_ifd_indices.append(index)
                elif rule.action == "replace":
                    self.replace_associated_image(ifds, index, rule, temp_dir)
        return [ifd for ids, ifd in enumerate(ifds) if ids not in delete_ifd_indices]

    def execute_plan(self, working_dir: Path) -> None:
        """Modify the image data according to the redaction rules."""
        ifds = self.tiff_info["ifds"]
        new_ifds = self._redact_associated_images(ifds, working_dir)
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
