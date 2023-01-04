from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import re
from typing import TYPE_CHECKING

import tifftools

if TYPE_CHECKING:
    from tifftools.tifftools import TagEntry


@dataclass
class TiffEntry:
    tag: tifftools.TiffTag
    entry: TagEntry


class RuleType(Enum):
    METADATA = 1
    IMAGE = 2


class RedactMethod(Enum):
    REPLACE = 1
    DELETE = 2
    KEEP = 3


# TODO implement ImageRules


@dataclass
class MetadataRule(ABC):
    """Represents an action to take for metadata."""

    title: str
    redact_method: RedactMethod

    @abstractmethod
    def is_match(self) -> bool:
        """Checks if this rule matches some piece of metadata."""


@dataclass
class TiffTagRule(MetadataRule):
    """Represents a rule that matches a given tiff tag, regardless of value."""

    tag: tifftools.TiffTag

    def is_match(self, entry: TiffEntry) -> bool:
        return self.tag.value == entry.tag.value


@dataclass
class TiffValueRegexRule(MetadataRule):
    """Represents a rule that checks both tiff tag and value."""

    tag: tifftools.TiffTag
    regex: str

    def is_match(self, entry: TiffEntry) -> bool:
        return self.tag.value == entry.tag.value and re.match(self.regex, entry.value) is not None


@dataclass
class MetadataRuleSet:
    tiff_rules: list[MetadataRule]
    # additional lists of rules for supported formats
