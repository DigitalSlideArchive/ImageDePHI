from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import tifftools

if TYPE_CHECKING:
    from tifftools.tifftools import IFD


class RuleType(Enum):
    METADATA = "metadata"
    IMAGE = "image"


class RedactMethod(Enum):
    REPLACE = "replace"
    DELETE = "delete"
    KEEP = "keep"


class RuleFormat(Enum):
    TIFF = "tiff"


class RuleSource(Enum):
    BASE = "base"
    OVERRIDE = "override"


@dataclass
class Rule:
    title: str
    redact_method: RedactMethod
    rule_type: RuleType

    # Consider factory class fn here
    # def make(...):

    def get_title(self) -> str:
        """Generate a title for the rule."""
        return self.title


@dataclass
class TiffMetadataRule(Rule):
    tag: tifftools.TiffTag
    replace_value: str | bytes | list[int | float]

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


def _make_tiff_metadata_rule(rule: dict) -> TiffMetadataRule:
    """Transform a rule from schema into an object."""
    tag = tifftools.constants.Tag[rule["tag"]]
    return TiffMetadataRule(
        title=rule["title"],
        redact_method=RedactMethod[rule["method"].upper()],
        rule_type=RuleType.METADATA,
        tag=tag,
        replace_value=rule.get("new_value", ""),
    )


_rule_function_mapping = {RuleFormat.TIFF: {RuleType.METADATA: _make_tiff_metadata_rule}}


def make_rule(rule_format: RuleFormat, rule_type: RuleType, rule: dict) -> Rule:
    rule_function = _rule_function_mapping[rule_format][rule_type]
    return rule_function(rule)
