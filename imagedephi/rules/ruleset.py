from dataclasses import dataclass

from .rule import FileFormat, Rule, RuleSource, RuleType
from .svs import MetadataSvsRule
from .tiff import MetadataTiffRule


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
