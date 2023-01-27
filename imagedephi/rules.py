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


class FileFormat(Enum):
    TIFF = "tiff"


class RuleSource(Enum):
    BASE = "base"
    OVERRIDE = "override"


@dataclass
class Rule:
    title: str
    redact_method: RedactMethod
    rule_type: RuleType
    rule_source: RuleSource

    # Consider factory class fn here
    # def make(...):

    def get_title(self) -> str:
        """Generate a title for the rule."""
        return self.title


@dataclass
class TiffMetadataRule(Rule):
    tag: tifftools.TiffTag
    replace_value: str | bytes | list[int | float] | None

    def is_match(self, tag: tifftools.TiffTag) -> bool:
        return self.tag.value == tag.value

    def apply(self, ifd: IFD):
        if self.redact_method == RedactMethod.DELETE:
            del ifd["tags"][self.tag.value]
        elif self.redact_method == RedactMethod.REPLACE:
            # If rules are constructed via make_rule, this should not be an issue
            if self.replace_value is None:
                raise RuntimeError(
                    f"A rule with redaction method {self.redact_method} "
                    "must have a valid replacement value."
                )
            ifd["tags"][self.tag.value]["data"] = self.replace_value
        elif self.redact_method == RedactMethod.KEEP:
            pass


@dataclass
class RuleSet:
    name: str
    description: str
    rules: dict[FileFormat, list[Rule]]


def _make_tiff_metadata_rule(rule: dict, source: RuleSource) -> TiffMetadataRule:
    """Transform a rule from schema into an object."""
    tag = tifftools.constants.Tag[rule["tag"]]
    redact_method = RedactMethod[rule["method"].upper()]
    return TiffMetadataRule(
        title=rule["title"],
        redact_method=redact_method,
        rule_type=RuleType.METADATA,
        rule_source=source,
        tag=tag,
        replace_value=rule["new_value"] if redact_method == RedactMethod.REPLACE else None,
    )


_rule_function_mapping = {FileFormat.TIFF: {RuleType.METADATA: _make_tiff_metadata_rule}}


def make_rule(file_format: FileFormat, rule_type: RuleType, rule: dict, source: RuleSource) -> Rule:
    rule_function = _rule_function_mapping[file_format][rule_type]
    return rule_function(rule, source)
