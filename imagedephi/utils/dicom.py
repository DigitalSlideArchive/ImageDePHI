from pathlib import Path
import re

import pydicom
from pydicom.tag import Tag

extensions = {
    None: True,
    "dcm": True,
    "dic": True,
    "dicom": True,
}


def file_is_same_series_as(original_path: Path, path: Path) -> bool:
    """
    Determine if path belongs to the same series as original_path.

    These heuristics match those defined in the large image DICOM source found at
    https://github.com/girder/large_image/blob/master/sources/dicom/large_image_source_dicom/__init__.py#L226.
    """

    might_match = False
    if original_path.suffix not in extensions:
        if original_path.suffix == path.suffix or path.suffix in extensions:
            might_match = True
    if (
        not might_match
        and re.match(r"^([1-9][0-9]*|0)(\.([1-9][0-9]*|0))+$", str(path))
        and len(str(path)) <= 64
    ):
        might_match = True
    if not might_match and re.match(r"^DCM_\d+$", str(path)):
        might_match = True
    if might_match:
        original = pydicom.dcmread(original_path, stop_before_pixels=True)
        original_series_uid = original.data_element("SeriesInstanceUID")
        if original_series_uid:
            original_series_uid = original_series_uid.value
            slide_to_test = pydicom.dcmread(path, stop_before_pixels=True)
            slide_series_uid = slide_to_test.data_element("SeriesInstanceUID")
            return slide_series_uid is not None and slide_series_uid.value == original_series_uid
    return False
