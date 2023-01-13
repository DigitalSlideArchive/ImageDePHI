from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import tifftools

if TYPE_CHECKING:
    from tifftools.tifftools import IFD, TagEntry


@dataclass
class TiffTagEntry:
    tag: tifftools.TiffTag
    entry: TagEntry


class RuleType(Enum):
    METADATA = 1
    IMAGE = 2


class RedactMethod(Enum):
    REPLACE = 1
    DELETE = 2
    KEEP = 3


class RuleFormat(Enum):
    TIFF = 1


class RuleSource(Enum):
    BASE = 1
    OVERRIDE = 2


@dataclass
class Rule:
    title: str
    redact_method: RedactMethod
    rule_type: RuleType


@dataclass
class TiffMetadataRule(Rule):
    tag: tifftools.TiffTag
    replace_value: str | bytes | list[int | float]
    rule_type = RuleType.METADATA

    def is_match(self, tag: tifftools.TiffTag) -> bool:
        return self.tag.value == tag.value

    def apply(self, ifd: IFD):
        if self.redact_method == RedactMethod.DELETE:
            del ifd["tags"][self.tag.value]
        elif self.redact_method == RedactMethod.REPLACE:
            ifd["tags"][self.tag.value]["data"] = self.replace_value
        elif self.redact_method == RedactMethod.KEEP:
            pass


@dataclass
class RuleSet:
    name: str
    description: str
    rules: dict[RuleFormat, list[Rule]]


def make_tiff_metadata_rule(rule: dict) -> TiffMetadataRule:
    """Transform a rule from schema into an object."""
    tag = tifftools.constants.Tag[rule["tag"]]
    return TiffMetadataRule(
        rule["title"],
        RedactMethod[rule["method"].upper()],
        RuleType.METADATA,
        tag,
        rule.get("new_value", ""),
    )


rule_function_mapping = {RuleFormat.TIFF: {RuleType.METADATA: make_tiff_metadata_rule}}


def make_rule(rule_format: RuleFormat, rule_type: RuleType, rule: dict) -> Rule:
    rule_function = rule_function_mapping[rule_format][rule_type]
    return rule_function(rule)
