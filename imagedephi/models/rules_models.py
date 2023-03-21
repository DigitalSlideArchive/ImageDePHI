import abc
import importlib.resources
from typing import Annotated, Literal

from pydantic import BaseModel, Field
import yaml


class Rule(BaseModel, abc.ABC):
    description: str | None = None


class MetadataRule(Rule):
    type: Literal["metadata"]


class TagMetadataRule(MetadataRule):
    tag_name: str


class ReplaceTagMetadataRule(TagMetadataRule):
    method: Literal["replace"]
    new_value: str


class KeepTagMetadataRule(TagMetadataRule):
    method: Literal["keep"]


class DeleteTagMetadataRule(TagMetadataRule):
    method: Literal["delete"]


class KeyMetadataRule(MetadataRule):
    key_name: str


class ReplaceKeyMetadataRule(KeyMetadataRule):
    method: Literal["replace"]
    new_value: str


class KeepKeyMetadataRule(KeyMetadataRule):
    method: Literal["keep"]


class DeleteKeyMetadataRule(KeyMetadataRule):
    method: Literal["delete"]


class Rules(BaseModel):
    # Pydantic needs to know which concrete rule types can actually be instantiated
    # and how to descriminate among them
    tiff: list[
        Annotated[
            ReplaceTagMetadataRule | KeepTagMetadataRule | DeleteTagMetadataRule,
            Field(discriminator="method"),
        ]
    ] | None
    svs: list[
        Annotated[
            ReplaceKeyMetadataRule | KeepKeyMetadataRule | DeleteKeyMetadataRule,
            Field(discriminator="method"),
        ]
    ] | None


class RuleFile(BaseModel):
    name: str
    description: str
    rules: Rules


base_rules_path = importlib.resources.files("imagedephi") / "base_rules.yaml"

with base_rules_path.open() as stream:
    rules_model = RuleFile.parse_obj(yaml.safe_load(stream))

print(rules_model)
assert isinstance(rules_model, RuleFile)
assert rules_model.rules.tiff is not None
assert isinstance(rules_model.rules.tiff[0], KeepTagMetadataRule)
assert isinstance(rules_model.rules.tiff[6], DeleteTagMetadataRule)
