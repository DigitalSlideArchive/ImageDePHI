from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, validator


class FileFormat(Enum):
    TIFF = "tiff"
    SVS = "svs"


class _MetadataRule(BaseModel):
    # key_name is not set by users, but is availible internally
    key_name: str = Field(exclude=True)
    action: Literal["keep", "delete", "replace"]


class ReplaceMetadataRule(_MetadataRule):
    action: Literal["replace"]
    new_value: str


class KeepMetadataRule(_MetadataRule):
    action: Literal["keep"]


class DeleteMetadataRule(_MetadataRule):
    action: Literal["delete"]


ConcreteMetadataRule = Annotated[
    ReplaceMetadataRule | KeepMetadataRule | DeleteMetadataRule, Field(discriminator="action")
]


class BaseRules(BaseModel):
    matches: list[str]


class TiffRules(BaseModel):
    metadata: dict[str, ConcreteMetadataRule]

    # TODO: is pre necessary?
    @validator("metadata", pre=True)
    @classmethod
    def set_tag_name(cls, metadata: Any):
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                if isinstance(value, dict):
                    value["key_name"] = key
        return metadata


class SvsRules(TiffRules):
    image_description: dict[str, ConcreteMetadataRule]

    # TODO: is pre necessary?
    @validator("metadata", "image_description", pre=True)
    @classmethod
    def set_tag_name(cls, metadata: Any):
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                if isinstance(value, dict):
                    value["key_name"] = key
        return metadata


class Ruleset(BaseModel):
    name: str
    description: str
    tiff: TiffRules
    svs: SvsRules
