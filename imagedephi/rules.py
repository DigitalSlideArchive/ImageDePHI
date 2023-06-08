from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, validator


class FileFormat(Enum):
    TIFF = "tiff"
    SVS = "svs"


class _Rule(BaseModel):
    # key_name is not set by users, but is availible internally
    key_name: str = Field(exclude=True)
    action: Literal["keep", "delete", "replace"]


class KeepRule(_Rule):
    action: Literal["keep"]


class DeleteRule(_Rule):
    action: Literal["delete"]


class ReplaceRule(_Rule):
    action: Literal["replace"]


class MetadataReplaceRule(ReplaceRule):
    new_value: str


class ImageReplaceRule(ReplaceRule):
    replace_with: Literal["blank_image"]


ConcreteMetadataRule = Annotated[
    MetadataReplaceRule | KeepRule | DeleteRule, Field(discriminator="action")
]

ConcreteImageRule = Annotated[
    ImageReplaceRule | KeepRule | DeleteRule, Field(discriminator="action")
]


class BaseRules(BaseModel):
    matches: list[str]


class TiffRules(BaseModel):
    associated_images: dict[str, ConcreteImageRule]
    metadata: dict[str, ConcreteMetadataRule]

    # TODO: is pre necessary?
    @validator("metadata", "associated_images", pre=True)
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
    @validator("metadata", "image_description", "associated_images", pre=True)
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
