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
    endianPack: Literal['>', '<']
    firstifd: int

class IFD(TypedDict):
    offset: int
    tags: dict[int, TagEntry]
    path_or_fobj: _PathOrStream
    size: int
    bigEndian: bool
    bigtiff: bool
    tagcount: int

class TagEntry(TypedDict, total=False):
    datatype: int
    count: int
    datapos: int
    offset: int
    ifds: list[list[IFD]]
    data: str | bytes | list[int | float]

def read_tiff(path: _PathOrStream) -> TiffInfo: ...
def write_tiff(
    ifds: TiffInfo | IFD | list[IFD],
    path: _PathOrStream,
    bigEndian: bool | None = ...,
    bigtiff: bool | None = ...,
    allowExisting: bool = ...,
    ifdsFirst: bool = ...,
) -> None: ...
