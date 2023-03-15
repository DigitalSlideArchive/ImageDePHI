import abc
import importlib.resources
from typing import Annotated, Literal

from pydantic import BaseModel, Field
import yaml


class Rule(BaseModel, abc.ABC):
    description: str | None = None
    tag_name: str
    method: Literal["replace", "keep", "delete"]
    type: str

class ReplaceRule(Rule):
    method: Literal["replace"]
    new_value: str


class KeepRule(Rule):
    method: Literal["keep"]


class DeleteRule(Rule):
    method: Literal["delete"]


# Pydantic needs to know which concrete rule types can actually be instantiated
# and how to descriminate among them
_ConcreteRule = Annotated[ReplaceRule | KeepRule | DeleteRule, Field(discriminator='method')]

class RuleFile(BaseModel):
    name: str
    description: str
    rules: dict[str, list[_ConcreteRule]]  # can add svs in future


base_rules_path = importlib.resources.files("imagedephi") / "base_rules.yaml"

with base_rules_path.open() as stream:
    rules_model = RuleFile.parse_obj(yaml.safe_load(stream))

print(rules_model)
assert isinstance(rules_model, RuleFile)
assert isinstance(rules_model.rules['tiff'][0], KeepRule)
assert isinstance(rules_model.rules['tiff'][6], DeleteRule)
assert issubclass(_ConcreteRule, Rule)
