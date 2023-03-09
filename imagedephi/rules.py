from __future__ import annotations

import abc
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, TypeVar

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
    SVS = "svs"


class RuleSource(Enum):
    BASE = "base"
    OVERRIDE = "override"


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


class Rule(abc.ABC):
    description: str | None
    redact_method: RedactMethod
    rule_type: RuleType
    rule_source: RuleSource

    def __init__(self, rule_spec: dict, rule_source: RuleSource) -> None:
        self.description = rule_spec.get("description", None)
        self.redact_method = RedactMethod[rule_spec["method"].upper()]
        self.rule_source = rule_source

    def get_description(self) -> str:
        """Generate a title for the rule."""
        return self.description if self.description else ""


class MetadataRuleMixin(Rule):
    rule_type = RuleType.METADATA

    @classmethod
    def build(
        cls: type[MetadataRuleMixinT], rule_spec: dict, rule_source: RuleSource
    ) -> MetadataRuleMixinT:
        redact_method = RedactMethod[rule_spec["method"].upper()]
        for rule_class in cls.__subclasses__():
            if rule_class.redact_method == redact_method:
                return rule_class(rule_spec, rule_source)
        else:
            raise Exception("Unknown redact_method.")


MetadataRuleMixinT = TypeVar("MetadataRuleMixinT", bound=MetadataRuleMixin)


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


class KeepMetadataTiffRule(MetadataTiffRule):
    redact_method = RedactMethod.KEEP

    def apply(self, ifd: IFD):
        pass


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


class SvsRule(Rule):
    @abc.abstractmethod
    def apply(self, svs_description: SvsDescription):
        ...


class MetadataSvsRule(SvsRule, MetadataRuleMixin):
    key: str

    def __init__(self, rule_spec: dict, rule_source: RuleSource) -> None:
        super().__init__(rule_spec, rule_source)
        self.key = rule_spec["key_name"]

    def is_match(self, key: str) -> bool:
        return self.key == key

    @abc.abstractmethod
    def apply(self, svs_description: SvsDescription):
        ...

    def get_description(self) -> str:
        if self.description:
            return self.description
        return (
            f"SVS Image Description - "
            f"{self.key}: {self.redact_method.value} ({self.rule_source.value})"
        )


class ReplaceMetadataSvsRule(MetadataSvsRule):
    redact_method = RedactMethod.REPLACE
    replace_value: str

    def __init__(self, rule_spec: dict, source: RuleSource):
        super().__init__(rule_spec, source)
        self.replace_value = rule_spec["new_value"]

    def apply(self, svs_description: SvsDescription):
        svs_description.metadata[self.key] = self.replace_value


class DeleteMetadataSvsRule(MetadataSvsRule):
    redact_method = RedactMethod.DELETE

    def apply(self, svs_description: SvsDescription):
        del svs_description.metadata[self.key]


class KeepMetadataSvsRule(MetadataSvsRule):
    redact_method = RedactMethod.KEEP

    def apply(self, svs_description: SvsDescription):
        pass


@dataclass
class RuleSet:
    name: str
    description: str
    rules: dict[FileFormat, list[Rule]]

    def get_metadata_tiff_rules(self) -> list[MetadataTiffRule]:
        if FileFormat.TIFF in self.rules:
            return [
                rule for rule in self.rules[FileFormat.TIFF] if isinstance(rule, MetadataTiffRule)
            ]
        return []

    def get_metadata_svs_rules(self) -> list[MetadataSvsRule]:
        if FileFormat.SVS in self.rules:
            return [
                rule for rule in self.rules[FileFormat.SVS] if isinstance(rule, MetadataSvsRule)
            ]
        return []


def _build_rule(file_format: FileFormat, rule_spec: dict, rule_source: RuleSource) -> Rule:
    rule_type = RuleType[rule_spec["type"].upper()]
    if file_format == FileFormat.TIFF:
        if rule_type == RuleType.METADATA:
            return MetadataTiffRule.build(rule_spec, rule_source)
    if file_format == FileFormat.SVS:
        if rule_type == RuleType.METADATA:
            return MetadataSvsRule.build(rule_spec, rule_source)

    raise Exception("Unsupported rule.")


def build_ruleset(ruleset_spec: dict, rule_source: RuleSource) -> RuleSet:
    """Read in metadata redaction rules from a file."""
    rule_set_rules = {}
    for file_format_key, rule_specs in ruleset_spec["rules"].items():
        file_format = FileFormat[file_format_key.upper()]
        rule_set_rules[file_format] = [
            _build_rule(file_format, rule_spec, rule_source) for rule_spec in rule_specs
        ]
    return RuleSet(ruleset_spec["name"], ruleset_spec["description"], rule_set_rules)
