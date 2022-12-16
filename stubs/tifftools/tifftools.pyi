from __future__ import annotations

from os import PathLike
from typing import BinaryIO, Literal, TypeAlias, TypedDict

_PathOrStream: TypeAlias = str | PathLike[str] | BinaryIO

class TiffInfo(TypedDict):
    ifds: list[IFD]
    path_or_fobj: _PathOrStream
    size: int
    header: bytes
    bigEndian: bool
    bigtiff: bool
    endianPack: Literal[">", "<"]
    firstifd: int

class IFD(TypedDict):
    offset: int
    tags: dict[int, TagEntry]
    path_or_fobj: _PathOrStream
    size: int
    bigEndian: bool
    bigtiff: bool
    tagcount: int

# TODO: Merge _BaseTagEntry and TagEntry, once NotRequired can be used in Python 3.11
class _BaseTagEntry(TypedDict):
    datatype: int
    count: int
    datapos: int
    data: str | bytes | list[int | float]

class TagEntry(_BaseTagEntry, total=False):
    offset: int
    ifds: list[list[IFD]]

def read_tiff(path: _PathOrStream) -> TiffInfo: ...
def write_tiff(
    ifds: TiffInfo | IFD | list[IFD],
    path: _PathOrStream,
    bigEndian: bool | None = ...,
    bigtiff: bool | None = ...,
    allowExisting: bool = ...,
    ifdsFirst: bool = ...,
) -> None: ...
