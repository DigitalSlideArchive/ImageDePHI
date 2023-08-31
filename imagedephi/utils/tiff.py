from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

import tifftools

if TYPE_CHECKING:
    from tifftools.tifftools import IFD, TiffInfo


IMAGE_DESCRIPTION_ID = tifftools.constants.Tag["ImageDescription"].value
NEWSUBFILETYPE_ID = tifftools.constants.Tag["NewSubfileType"].value


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
            if tag.isIFD():
                # entry['ifds'] contains a list of lists
                # see tifftools.read_tiff
                for sub_ifds in entry.get("ifds", []):
                    yield from iter_ifds(sub_ifds, tag.get("tagset"))
        yield ifd


def is_tiled(ifd: IFD):
    """Determine if an IFD represents a tiled image."""
    return tifftools.Tag.TileWidth.value in ifd["tags"]


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


def _get_macro(ifds: list[IFD]) -> IFD | None:
    key = "macro"
    for ifd in iter_ifds(ifds):
        if IMAGE_DESCRIPTION_ID in ifd["tags"]:
            if key in str(ifd["tags"][IMAGE_DESCRIPTION_ID]["data"]):
                return ifd
        if NEWSUBFILETYPE_ID in ifd["tags"]:
            newsubfiletype = ifd["tags"][NEWSUBFILETYPE_ID]["data"][0]
            if newsubfiletype == 9:
                return ifd
    return None


def _get_label(ifds: list[IFD]) -> IFD | None:
    key = "label"
    for ifd in iter_ifds(ifds):
        if IMAGE_DESCRIPTION_ID in ifd["tags"]:
            if key in str(ifd["tags"][IMAGE_DESCRIPTION_ID]["data"]):
                return ifd
        # Check NewSubfileType/tiled or non tiled
        if not is_tiled(ifd) and NEWSUBFILETYPE_ID in ifd["tags"]:
            if ifd["tags"][NEWSUBFILETYPE_ID]["data"][0] == 1:
                return ifd
    return None


def get_associated_image_svs(image_path: Path, image_key: str) -> IFD | None:
    """Given a path to an SVS image, return the IFD for a given associated label or macro image."""
    if image_key not in ["macro", "label"]:
        raise ValueError("image_key must be one of macro, label")

    image_info = tifftools.read_tiff(image_path)
    ifds = image_info["ifds"]

    if "aperio" not in str(ifds[0]["tags"][IMAGE_DESCRIPTION_ID]["data"]).lower():
        return None

    if image_key == "macro":
        return _get_macro(ifds)
    elif image_key == "label":
        return _get_label(ifds)
    return None


def get_ifd_for_thumbnail(image_path: Path) -> IFD | None:
    """Given a path to a TIFF image, return the IFD for the lowest resolution tiled image."""
    image_info = tifftools.read_tiff(image_path)

    min_width = float("inf")
    lowest_res_ifd = None
    for ifd in iter_ifds(image_info["ifds"]):
        # We are interested in the lowest res tiled image.
        if tifftools.Tag.TileWidth.value not in ifd["tags"]:
            continue

        image_width = int(ifd["tags"][tifftools.Tag.ImageWidth.value]["data"][0])
        if image_width and (not min_width or image_width < min_width):
            min_width = int(image_width)
            lowest_res_ifd = ifd

    return lowest_res_ifd


def get_is_svs(image_path: Path) -> bool:
    image_info = tifftools.read_tiff(image_path)
    if tifftools.Tag.ImageDescription.value not in image_info["ifds"][0]["tags"]:
        return False
    image_description = image_info["ifds"][0]["tags"][tifftools.Tag.ImageDescription.value]["data"]
    return "aperio" in str(image_description).lower()
