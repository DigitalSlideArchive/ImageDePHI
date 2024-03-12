from pathlib import Path

from imagedephi.rules import FileFormat


def get_file_format_from_path(image_path: Path) -> FileFormat | None:
    """
    Attempt to determine the file type of an image by looking at its file signature.

    See https://en.wikipedia.org/wiki/List_of_file_signatures. In case of a "dual-flavor" DICOM
    file (i.e. a file that can be read as a DICOM or a tiff), prefer to report the image as
    DICOM.
    """
    data = open(image_path, "rb").read(132)
    if data[128:] == b"DICM":
        return FileFormat.DICOM
    elif data[:4] in (b"II\x2a\x00", b"MM\x00\x2a", b"II\x2b\x2a", b"MM\x00\x2b"):
        return FileFormat.TIFF
    return None
