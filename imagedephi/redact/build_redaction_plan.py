from pathlib import Path

from imagedephi.rules import FileFormat, Ruleset
from imagedephi.utils.image import get_file_format_from_path
from imagedephi.utils.tiff import get_is_svs

from .dicom import DicomRedactionPlan
from .redaction_plan import RedactionPlan
from .svs import SvsRedactionPlan
from .tiff import TiffRedactionPlan, UnsupportedFileTypeError


class ImageDePHIRedactionError(Exception):
    """Thrown when the program encounters problems with current configuration and image files."""


def build_redaction_plan(
    image_path: Path,
    base_rules: Ruleset,
    override_rules: Ruleset | None = None,
    dcm_uid_map: dict[str, str] | None = None,
) -> RedactionPlan:
    file_format = get_file_format_from_path(image_path)
    strict = override_rules.strict if override_rules else base_rules.strict
    if file_format == FileFormat.TIFF:
        if get_is_svs(image_path):
            merged_svs_rules = base_rules.svs.copy()
            if override_rules:
                merged_svs_rules.metadata.update(override_rules.svs.metadata)
                merged_svs_rules.associated_images.update(override_rules.svs.associated_images)
                merged_svs_rules.image_description.update(override_rules.svs.image_description)
            return SvsRedactionPlan(image_path, merged_svs_rules, strict)
        else:
            merged_tiff_rules = base_rules.tiff.copy()
            if override_rules:
                merged_tiff_rules.metadata.update(override_rules.tiff.metadata)
                merged_tiff_rules.associated_images.update(override_rules.tiff.associated_images)
            return TiffRedactionPlan(image_path, merged_tiff_rules, strict)
    elif file_format == FileFormat.DICOM:
        if strict:
            raise ImageDePHIRedactionError(
                "strict redaction is not currently supported for DICOM images"
            )
        dicom_rules = base_rules.dicom.copy()
        if override_rules:
            dicom_rules.metadata.update(override_rules.dicom.metadata)
            dicom_rules.custom_metadata_action = override_rules.dicom.custom_metadata_action
            dicom_rules.associated_images.update(override_rules.dicom.associated_images)
        return DicomRedactionPlan(image_path, dicom_rules, dcm_uid_map)
    else:
        raise UnsupportedFileTypeError(f"File format for {image_path} not supported.")
