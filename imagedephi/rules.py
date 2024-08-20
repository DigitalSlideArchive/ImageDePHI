from enum import Enum
from typing import Annotated, Any, Literal, Type, TypeAlias

from pydantic import BaseModel, Field, validator


class FileFormat(Enum):
    TIFF = "tiff"
    SVS = "svs"
    DICOM = "dicom"


expected_type_map: dict[str, list[Type[Any]]] = {
    "integer": [int],
    "number": [int, float],
    "text": [str],
    "rational": [int],
}

RedactionOperation: TypeAlias = Literal[
    "keep",
    "delete",
    "replace",
    "empty",
    "replace_uid",
    "replace_dummy",
    "modify_date",
]


class _Rule(BaseModel):
    # key_name is not set by users, but is availible internally
    key_name: str = Field(exclude=True)
    action: Literal[
        "keep",
        "delete",
        "replace",
        "replace_uid",
        "replace_dummy",
        "empty",
        "check_type",
        "modify_date",
    ]


class KeepRule(_Rule):
    action: Literal["keep"]


class DeleteRule(_Rule):
    action: Literal["delete"]


class EmptyRule(_Rule):
    """Replace with a zero-length value."""

    action: Literal["empty"]


class ReplaceRule(_Rule):
    action: Literal["replace"]


class MetadataReplaceRule(ReplaceRule):
    new_value: str


class ModifyDateRule(_Rule):
    action: Literal["modify_date"]


class ImageReplaceRule(ReplaceRule):
    replace_with: Literal["blank_image"]


class CheckTypeMetadataRule(_Rule):
    action: Literal["check_type"]
    expected_type: Literal["number", "integer", "text", "rational"]
    valid_data_types: list[Type[Any]] = []
    expected_count: int = 1

    @validator("valid_data_types", pre=True, always=True)
    @classmethod
    def set_valid_data_types(
        cls, valid_data_types: list[Type[Any]], values: dict[str, Any]
    ) -> list[Type[Any]]:
        valid_data_types = expected_type_map[values["expected_type"]]
        return valid_data_types


class UidReplaceRule(_Rule):
    action: Literal["replace_uid"]


class DummyReplaceRule(_Rule):
    """Replace value with a system-defined value based on original type."""

    action: Literal["replace_dummy"]


ConcreteMetadataRule = Annotated[
    MetadataReplaceRule
    | KeepRule
    | DeleteRule
    | CheckTypeMetadataRule
    | UidReplaceRule
    | EmptyRule
    | DummyReplaceRule
    | ModifyDateRule,
    Field(discriminator="action"),
]

ConcreteImageRule = Annotated[
    ImageReplaceRule | KeepRule | DeleteRule, Field(discriminator="action")
]


class BaseRules(BaseModel):
    matches: list[str]


class TiffRules(BaseModel):
    associated_images: dict[str, ConcreteImageRule] = {}
    metadata: dict[str, ConcreteMetadataRule] = {}
    metadata_fallback_action: Literal["delete"] | Literal["keep"] | None = None
    associated_image_fallback: ConcreteImageRule | None = None

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
    image_description: dict[str, ConcreteMetadataRule] = {}

    # TODO: is pre necessary?
    @validator("metadata", "image_description", "associated_images", pre=True)
    @classmethod
    def set_tag_name(cls, metadata: Any):
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                if isinstance(value, dict):
                    value["key_name"] = key
        return metadata


class DicomRules(BaseModel):
    metadata: dict[str, ConcreteMetadataRule] = {}
    associated_images: dict[str, ConcreteImageRule] = {}
    custom_metadata_action: Literal["keep"] | Literal["delete"] | Literal["use_rule"] = "delete"

    @validator("metadata", "associated_images", pre=True)
    @classmethod
    def set_tag_name(cls, metadata: Any):
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                if isinstance(value, dict):
                    value["key_name"] = key
        return metadata


class Ruleset(BaseModel):
    name: str = "My Rules"
    description: str = "My rules"
    output_file_name: str = "study_slide"
    tiff: TiffRules = TiffRules()
    svs: SvsRules = SvsRules()
    dicom: DicomRules = DicomRules()
