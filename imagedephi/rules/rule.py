from __future__ import annotations

import abc
from enum import Enum
from typing import TypeVar


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
