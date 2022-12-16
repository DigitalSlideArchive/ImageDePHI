from __future__ import annotations

from .constants import Datatype, Tag, TiffDatatype, TiffTag
from .exceptions import MustBeBigTiffError, TifftoolsError, UnknownTagError
from .tifftools import read_tiff, write_tiff

__version__: str

__all__ = [
    "Datatype",
    "TiffDatatype",
    "Tag",
    "TiffTag",
    "TifftoolsError",
    "UnknownTagError",
    "MustBeBigTiffError",
    "read_tiff",
    "write_tiff",
    "__version__",
]
