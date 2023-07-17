from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import tifftools

if TYPE_CHECKING:
    from tifftools.tifftools import IFD


def iter_ifds(
    ifds: list[IFD],
    tag_set=tifftools.constants.Tag,
) -> Generator[IFD, None, None]:
    for ifd in ifds:
        for tag_id, entry in ifd["tags"].items():
            tag: tifftools.TiffTag = tifftools.constants.get_or_create_tag(
                tag_id,
                tagSet=tag_set,
                datatype=tifftools.Datatype[entry["datatype"]],
            )
            if not tag.isIFD():
                yield ifd
            else:
                # entry['ifds'] contains a list of lists
                # see tifftools.read_tiff
                for sub_ifds in entry.get("ifds", []):
                    yield from iter_ifds(sub_ifds, tag.get("tagset"))
        yield ifd

def get_tiff_tag(tag_name: str) -> tifftools.TiffTag:
    """Given the name of a TIFF tag, attempt to return the TIFF tag from tifftools."""
    # This function checks TagSet objects from tifftools for a given tag. If the tag is not found
    # after exhausting the tag sets, a new tag is created.
    for tag_set in [
        tifftools.constants.Tag,
        tifftools.constants.GPSTag,
        tifftools.constants.EXIFTag,
    ]:
        if tag_name in tag_set:
            return tag_set[tag_name]
    return tifftools.constants.get_or_create_tag(tag_name)


def get_associated_image_svs(
        image_path: Path,
        image_key: Literal["macro"] | Literal["label"]
    ) -> IFD | None:
    """Given a path to an SVS image, return the IFD for a given associated label or macro image."""
    image_info = tifftools.read_tiff(image_path)
    image_description_tag = tifftools.constants.Tag["ImageDescription"]
    ifds = image_info["ifds"]

    if "Aperio" not in str(ifds[0]["tags"][image_description_tag.value]["data"]):
        # raise ValueError(f"{image_path} is not an svs image")
        return None

    for ifd in iter_ifds(ifds):
        if image_key in str(ifd["tags"][image_description_tag.value]["data"]):
            return ifd
    return None
