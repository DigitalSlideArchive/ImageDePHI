import importlib.resources
from typing import Literal

from pydantic import BaseModel
import yaml


class Replace(BaseModel):
    method: Literal["replace"]
    new_value: str


class Keep(BaseModel):
    method: Literal["keep"]


class Delete(BaseModel):
    method: Literal["delete"]


class Rule(BaseModel):
    description: str | None = None
    tag_name: str
    method: Literal["replace", "keep", "delete"]
    type: str


class Tiff(BaseModel):
    tiff: list[Rule]


class RuleFile(BaseModel):
    name: str
    description: str
    rules: Tiff  # can add svs in future


base_rules_path = importlib.resources.files("imagedephi") / "base_rules.yaml"

with base_rules_path.open() as stream:
    rules_model = yaml.safe_load(stream)
