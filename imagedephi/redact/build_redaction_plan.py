from pathlib import Path

from imagedephi.rules import FileFormat, Ruleset

from .dicom import DicomRedactionPlan
from .redaction_plan import RedactionPlan
from .svs import SvsRedactionPlan
from .tiff import TiffRedactionPlan, UnsupportedFileTypeError

FILE_EXTENSION_MAP: dict[str, FileFormat] = {
    ".tif": FileFormat.TIFF,
    ".tiff": FileFormat.TIFF,
    ".svs": FileFormat.SVS,
    ".dcm": FileFormat.DICOM,
}


def get_file_format_from_path(image_path: Path) -> FileFormat | None:
    try:
        data = open(image_path, "rb").read(132)
    except PermissionError:
        raise Exception(f"Could not open {image_path}")
    else:
        if data[:4] in (b"II\x2a\x00", b"MM\x00\x2a", b"II\x2b\x00", b"MM\x00\x2b"):
            # tiff
            return FileFormat.TIFF
        elif data[128:] == b"DICM":
            return FileFormat.DICOM
    return None


def build_redaction_plan(
    image_path: Path, base_rules: Ruleset, override_rules: Ruleset | None = None
) -> RedactionPlan:
    file_format = get_file_format_from_path(image_path)
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
                merged_rules.metadata.update(override_rules.tiff.metadata)

            return TiffRedactionPlan(image_path, merged_rules)
        elif file_extension == FileFormat.SVS:
            merged_rules = base_rules.svs.copy()
            if override_rules:
                merged_rules.metadata.update(override_rules.svs.metadata)
                merged_rules.image_description.update(override_rules.svs.image_description)
            return SvsRedactionPlan(image_path, merged_rules)
        else:
            raise UnsupportedFileTypeError(f"File format for {image_path} not supported.")
    elif file_format == FileFormat.DICOM:
        dicom_rules = base_rules.dicom.copy()
        if override_rules:
            dicom_rules.metadata.update(override_rules.dicom.metadata)
            dicom_rules.delete_custom_metadata = override_rules.dicom.delete_custom_metadata
        return DicomRedactionPlan(image_path, dicom_rules)
    else:
        raise UnsupportedFileTypeError(f"File format for {image_path} not supported.")
