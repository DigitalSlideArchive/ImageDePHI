import abc

from .rule import MetadataRuleMixin, RedactMethod, Rule, RuleSource


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
