from __future__ import annotations

import abc
from typing import TYPE_CHECKING

import tifftools

from .rule import ExpectedType, MetadataRuleMixin, RedactMethod, Rule, RuleSource, is_expected_type

if TYPE_CHECKING:
    from tifftools.tifftools import IFD


def _get_tiff_tag(tag_name: str) -> tifftools.TiffTag:
    """Given the name of a TIFF tag, attempt to return the TIFF tag from tifftools."""
    # This function checks TagSet objects from tifftools for a given tag. If the tag is not found
    # after exhausting the tag sets, a new tag is created.
    for tag_set in [
        tifftools.constants.Tag,
        tifftools.constants.GPSTag,
        tifftools.constants.EXIFTag,
    ]:
        if tag_name in tag_set:
            return tag_set[tag_name]
    return tifftools.constants.get_or_create_tag(tag_name)


class TiffRule(Rule):
    @abc.abstractmethod
    def apply(self, ifd: IFD):
        ...


class MetadataTiffRule(TiffRule, MetadataRuleMixin):
    tag: tifftools.TiffTag

    def __init__(self, rule_spec: dict, rule_source: RuleSource) -> None:
        """Transform a rule from schema into an object."""
        super().__init__(rule_spec, rule_source)
        self.tag = _get_tiff_tag(rule_spec["tag_name"])

    def is_match(self, tag: tifftools.TiffTag) -> bool:
        return self.tag.value == tag.value

    @abc.abstractmethod
    def apply(self, ifd: IFD):
        ...

    def get_description(self) -> str:
        if self.description:
            return self.description
        return (
            f"Tiff Tag {self.tag.value} - "
            f"{self.tag.name}: {self.redact_method.value} ({self.rule_source.value})"
        )


class ReplaceMetadataTiffRule(MetadataTiffRule):
    redact_method = RedactMethod.REPLACE
    replace_value: str | bytes | list[int | float]

    def __init__(self, rule_spec: dict, source: RuleSource) -> None:
        super().__init__(rule_spec, source)
        self.replace_value = rule_spec["new_value"]

    def apply(self, ifd: IFD):
        ifd["tags"][self.tag.value]["data"] = self.replace_value


class DeleteMetadataTiffRule(MetadataTiffRule):
    redact_method = RedactMethod.DELETE

    def apply(self, ifd: IFD):
        del ifd["tags"][self.tag.value]


class DataTypeMetadataTiffRule(MetadataTiffRule):
    redact_method = RedactMethod.DATATYPE
    expected_type: ExpectedType
    expected_count: int = 1

    def __init__(self, rule_spec: dict, source: RuleSource) -> None:
        super().__init__(rule_spec, source)
        self.expected_type = rule_spec["expected_type"]
        self.expected_count = rule_spec["expected_count"]

    def apply(self, ifd: IFD):
        if not is_expected_type(
            ifd["tags"][self.tag.value]["data"], self.expected_type, self.expected_count
        ):
            del ifd["tags"][self.tag.value]


class KeepMetadataTiffRule(MetadataTiffRule):
    redact_method = RedactMethod.KEEP

    def apply(self, ifd: IFD):
        pass
