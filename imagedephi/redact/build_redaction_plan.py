from pathlib import Path

from imagedephi.rules import FileFormat, Ruleset
from imagedephi.utils.image import get_file_format_from_path

from .dicom import DicomRedactionPlan
from .redaction_plan import RedactionPlan
from .svs import SvsRedactionPlan
from .tiff import TiffRedactionPlan, UnsupportedFileTypeError


class ImageDePHIRedactionError(Exception):
    """Thrown when the program encounters problems with current configuration and image files."""


FILE_EXTENSION_MAP: dict[str, FileFormat] = {
    ".tif": FileFormat.TIFF,
    ".tiff": FileFormat.TIFF,
    ".svs": FileFormat.SVS,
    ".dcm": FileFormat.DICOM,
}


def build_redaction_plan(
    image_path: Path,
    base_rules: Ruleset,
    override_rules: Ruleset | None = None,
    dcm_uid_map: dict[str, str] | None = None,
) -> RedactionPlan:
    file_format = get_file_format_from_path(image_path)
    strict = override_rules.strict if override_rules else base_rules.strict
    if file_format == FileFormat.TIFF:
        # Since SVS is a subset of tiff, fall back on file extension
        file_extension = (
            FILE_EXTENSION_MAP[image_path.suffix]
            if image_path.suffix in FILE_EXTENSION_MAP
            else file_format
        )
        if file_extension == FileFormat.TIFF:
            merged_rules = base_rules.tiff.copy()
            if override_rules:
                if override_rules.strict:
                    merged_rules = override_rules.tiff.copy()
                else:
                    merged_rules.metadata.update(override_rules.tiff.metadata)

            return TiffRedactionPlan(image_path, merged_rules, strict)
        elif file_extension == FileFormat.SVS:
            merged_rules = base_rules.svs.copy()
            if override_rules:
                if override_rules.strict:
                    merged_rules = override_rules.svs.copy()
                else:
                    merged_rules.metadata.update(override_rules.svs.metadata)
                    merged_rules.image_description.update(override_rules.svs.image_description)
            return SvsRedactionPlan(image_path, merged_rules, strict)
        else:
            raise UnsupportedFileTypeError(f"File format for {image_path} not supported.")
    elif file_format == FileFormat.DICOM:
        if strict:
            raise ImageDePHIRedactionError(
                "strict redaction is not currently supported for DICOM images"
            )
        dicom_rules = base_rules.dicom.copy()
        if override_rules:
            dicom_rules.metadata.update(override_rules.dicom.metadata)
            dicom_rules.delete_custom_metadata = override_rules.dicom.delete_custom_metadata
        return DicomRedactionPlan(image_path, dicom_rules, dcm_uid_map)
    else:
        raise UnsupportedFileTypeError(f"File format for {image_path} not supported.")
