from __future__ import annotations

from collections.abc import Generator
from typing import Any, Generic, TypeAlias, TypeVar, overload

# Anything can be set as a TiffConstant attribute
_TiffConstantAttr: TypeAlias = Any

class TiffConstant(int):
    value: int
    name: str
    def __init__(self, value: int, constantDict: dict[str, _TiffConstantAttr]) -> None: ...
    def __getitem__(self, key: str) -> _TiffConstantAttr: ...
    def get(self, key: str, default: _TiffConstantAttr = ...) -> _TiffConstantAttr: ...

_TiffConstantT = TypeVar("_TiffConstantT", bound=TiffConstant)

class TiffConstantSet(Generic[_TiffConstantT]):
    def __init__(
        self, setNameOrClass: _TiffConstantT | str, setDict: dict[str, _TiffConstantAttr]
    ) -> None: ...
    def __contains__(self, other: str | int) -> bool: ...
    def __getattr__(self, key: str) -> _TiffConstantT: ...
    def __getitem__(self, key: str | int | _TiffConstantT) -> _TiffConstantT: ...
    def __iter__(self) -> Generator[_TiffConstantT, None, None]: ...
    def get(
        self, key: str | int, default: _TiffConstantT | None = ...
    ) -> _TiffConstantT | None: ...

class TiffTag(TiffConstant):
    def isOffsetData(self) -> bool: ...
    def isIFD(self) -> bool: ...

Tag: TiffConstantSet[TiffTag]

Compression: TiffConstantSet

GPSTag: TiffConstantSet[TiffTag]

EXIFTag: TiffConstantSet[TiffTag]

class TiffDatatype(TiffConstant): ...

Datatype: TiffConstantSet[TiffDatatype]

# When tagSet is None or not provided, this returns a TiffTag
@overload
def get_or_create_tag(
    key: str | int,
    tagSet: None = ...,
    upperLimit: bool = ...,
    **tagOptions: _TiffConstantAttr,
) -> TiffTag: ...
@overload
def get_or_create_tag(
    key: str | int,
    tagSet: TiffConstantSet[_TiffConstantT],
    upperLimit: bool = ...,
    **tagOptions: _TiffConstantAttr,
) -> _TiffConstantT: ...
