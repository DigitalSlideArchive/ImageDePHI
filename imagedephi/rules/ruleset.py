from dataclasses import dataclass
from typing import Any

from .rule import FileFormat, RuleSource
from .svs import MetadataSvsRule
from .tiff import MetadataTiffRule, get_tiff_tag


class FileFormatRules:
    file_format: FileFormat
    metadata_rules: dict[Any, Any]


class TiffFormatRules(FileFormatRules):
    file_format = FileFormat.TIFF
    metadata_rules: dict[int, MetadataTiffRule]

    @staticmethod
    def build_tiff_metadata_rule(
        tag_name: str, method_spec: str | dict, rule_source: RuleSource
    ) -> MetadataTiffRule:
        rule_spec = {"tag_name": tag_name}
        if isinstance(method_spec, str):
            rule_spec["method"] = method_spec
        else:
            rule_spec = rule_spec | method_spec
        return MetadataTiffRule.build(rule_spec, rule_source)

    def __init__(self, file_format_spec: dict, rule_source: RuleSource):
        self.metadata_rules = {}
        for tag_name, method_info in file_format_spec["metadata"].items():
            tiff_tag = get_tiff_tag(tag_name)
            self.metadata_rules[tiff_tag.value] = TiffFormatRules.build_tiff_metadata_rule(
                tag_name, method_info, rule_source
            )


class SvsFormatRules(TiffFormatRules):
    file_format = FileFormat.SVS
    image_description_rules: dict[str, MetadataSvsRule]

    @staticmethod
    def build_svs_image_description_rule(
        key_name: str, method_spec: str | dict, rule_source: RuleSource
    ) -> MetadataSvsRule:
        rule_spec = {"key_name": key_name}
        if isinstance(method_spec, str):
            rule_spec["method"] = method_spec
        else:
            rule_spec = rule_spec | method_spec
        return MetadataSvsRule.build(rule_spec, rule_source)

    def __init__(self, file_format_spec: dict, rule_source: RuleSource):
        super().__init__(file_format_spec, rule_source)
        self.image_description_rules = {}
        for key_name, method_info in file_format_spec["image_description"].items():
            self.image_description_rules[
                key_name
            ] = SvsFormatRules.build_svs_image_description_rule(key_name, method_info, rule_source)


@dataclass
class RuleSet:
    name: str
    description: str
    tiff: TiffFormatRules
    svs: SvsFormatRules

    def get_format_rules(self, file_format: FileFormat) -> FileFormatRules:
        if file_format == FileFormat.TIFF:
            return self.tiff
        if file_format == FileFormat.SVS:
            return self.svs
        raise Exception(f"File format {file_format} not supported")


def build_ruleset(ruleset_spec: dict, rule_source: RuleSource) -> RuleSet:
    """Read in metadata redaction rules from a file."""
    rule_set_args = [ruleset_spec["name"], ruleset_spec["description"]]
    for file_format in FileFormat:
        format_rules = ruleset_spec.get(file_format.value, None)
        if not format_rules:
            raise Exception(f"No rules provided for format {file_format}")
        if file_format == FileFormat.TIFF:
            rule_set_args.append(TiffFormatRules(format_rules, rule_source))
        elif file_format == FileFormat.SVS:
            rule_set_args.append(SvsFormatRules(format_rules, rule_source))
    return RuleSet(*rule_set_args)
