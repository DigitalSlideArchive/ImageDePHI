from pathlib import Path

from imagedephi.rules import FileFormat


def get_file_format_from_path(image_path: Path) -> FileFormat | None:
    try:
        data = open(image_path, "rb").read(132)
    except PermissionError:
        raise Exception(f"Could not open {image_path}")
    else:
        if data[:4] in (b"II\x2a\x00", b"MM\x00\x2a", b"II\x2b\x2a", b"MM\x00\x2b"):
            return FileFormat.TIFF
        elif data[128:] == b"DCIM":
            return FileFormat.DICOM
    return None
