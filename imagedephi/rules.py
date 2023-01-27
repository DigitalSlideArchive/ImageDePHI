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
    description: str | None
    redact_method: RedactMethod
    rule_type: RuleType
    rule_source: RuleSource

    # Consider factory class fn here
    # def make(...):

    def get_description(self) -> str:
        """Generate a title for the rule."""
        return self.description if self.description else ""


@dataclass
class TiffMetadataRule(Rule):
    tag: tifftools.TiffTag
    replace_value: str | bytes | list[int | float] | None

    @classmethod
    def build(cls, rule_dict: dict, source: RuleSource) -> TiffMetadataRule:
        """Transform a rule from schema into an object."""
        tag = tifftools.constants.Tag[rule_dict["tag_name"]]
        redact_method = RedactMethod[rule_dict["method"].upper()]
        return TiffMetadataRule(
            description=rule_dict.get("description", None),  # this is optional
            redact_method=redact_method,
            rule_type=RuleType.METADATA,
            rule_source=source,
            tag=tag,
            replace_value=rule_dict["new_value"] if redact_method == RedactMethod.REPLACE else None,
        )

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

    def get_description(self) -> str:
        if self.description:
            return self.description
        return f"Tag {self.tag.value} - {self.tag.name}: {self.redact_method} ({self.rule_source})"


@dataclass
class RuleSet:
    name: str
    description: str
    rules: dict[FileFormat, dict[RuleType, list[Rule]]]

    def get_tiff_metadata_rules(self) -> list[TiffMetadataRule]:
        return [
            rule
            for rule in self.rules[FileFormat.TIFF][RuleType.METADATA]
            if isinstance(rule, TiffMetadataRule)
        ]


def _build_rule(
    file_format: FileFormat, rule_type: RuleType, rule_dict: dict, source: RuleSource
) -> Rule | None:
    if file_format == FileFormat.TIFF:
        if rule_type == RuleType.METADATA:
            return TiffMetadataRule.build(rule_dict, source)
    return None


def build_ruleset(rules_dict: dict, rule_source: RuleSource) -> RuleSet:
    """Read in metadata redaction rules from a file."""
    rule_set_rules = {}
    for file_format in rules_dict["rules"]:
        format_key = FileFormat[file_format.upper()]
        format_rules = rules_dict["rules"][file_format]
        format_rule_objects: dict[RuleType, list[Rule]] = {
            RuleType.IMAGE: [],
            RuleType.METADATA: [],
        }
        for rule in format_rules:
            rule_type = RuleType[rule["type"].upper()]
            rule = _build_rule(format_key, rule_type, rule, rule_source)
            if rule:
                format_rule_objects[rule_type].append(rule)
        rule_set_rules[format_key] = format_rule_objects
    return RuleSet(rules_dict["name"], rules_dict["description"], rule_set_rules)
