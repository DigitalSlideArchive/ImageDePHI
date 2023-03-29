from __future__ import annotations

import abc
from enum import Enum
from typing import Any, Type, TypeVar


class RuleType(Enum):
    METADATA = "metadata"
    IMAGE = "image"


class RedactMethod(Enum):
    REPLACE = "replace"
    DELETE = "delete"
    KEEP = "keep"
    DATATYPE = "datatype"


class FileFormat(Enum):
    TIFF = "tiff"
    SVS = "svs"


class RuleSource(Enum):
    BASE = "base"
    OVERRIDE = "override"


class ExpectedType(Enum):
    NUMBER = "number"


_expected_type_map: dict[ExpectedType, tuple[Type[Any]]] = {
    ExpectedType.NUMBER: tuple([int, float]),
}


def is_expected_type(value: Any, expected_type: ExpectedType, expected_count: int) -> bool:
    valid_types = _expected_type_map[expected_type]
    if isinstance(value, list):
        return len(value) == expected_count and all(isinstance(item, valid_types) for item in value)
    return isinstance(value, valid_types)


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
