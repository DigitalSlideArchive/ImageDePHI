from pathlib import Path

from imagedephi.rules import FileFormat, Ruleset

from .redaction_plan import RedactionPlan
from .svs import SvsRedactionPlan
from .tiff import TiffMetadataRedactionPlan

FILE_EXTENSION_MAP: dict[str, FileFormat] = {
    ".tif": FileFormat.TIFF,
    ".tiff": FileFormat.TIFF,
    ".svs": FileFormat.SVS,
}


def build_redaction_plan(
    image_path: Path, base_rules: Ruleset, override_rules: Ruleset | None = None
) -> RedactionPlan:
    file_extension = FILE_EXTENSION_MAP[image_path.suffix]
    if file_extension == FileFormat.TIFF:
        merged_rules = base_rules.tiff.copy()
        if override_rules:
            merged_rules.metadata.update(override_rules.tiff.metadata)

        return TiffMetadataRedactionPlan(image_path, merged_rules)
    elif file_extension == FileFormat.SVS:
        merged_rules = base_rules.svs.copy()
        if override_rules:
            merged_rules.metadata.update(override_rules.svs.metadata)
            merged_rules.image_description.update(override_rules.svs.image_description)

        return SvsRedactionPlan(image_path, merged_rules)
    else:
        raise Exception(f"File format for {image_path} not supported.")
