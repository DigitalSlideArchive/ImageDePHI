from __future__ import annotations

import argparse
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import tifftools
import tifftools.constants

if TYPE_CHECKING:
    from tifftools.tifftools import IFD, TiffInfo


class RedactMethod(Enum):
    REPLACE = 1
    DELETE = 2


def get_tags_to_redact() -> dict[int, dict[str, Any]]:
    return {
        270: {
            "id": 270,
            "name": "ImageDescription",
            "method": RedactMethod.REPLACE,
            "replace_value": "Redacted by ImageDePHI",
        }
    }


def redact_one_tag(ifd: IFD, tag: tifftools.TiffTag, redact_instructions: dict[str, Any]) -> None:
    if redact_instructions["method"] == RedactMethod.REPLACE:
        ifd["tags"][tag.value]["data"] = redact_instructions["replace_value"]
    elif redact_instructions["method"] == RedactMethod.DELETE:
        del ifd["tags"][tag.value]


def redact_tiff_tags(ifds: list[IFD], tags_to_redact: dict[int, dict[str, Any]]) -> None:
    for ifd in ifds:
        for tag_id, tag_info in sorted(ifd["tags"].items()):
            tag: tifftools.TiffTag = tifftools.constants.get_or_create_tag(
                tag_id,
                datatype=tifftools.Datatype[tag_info["datatype"]],
            )
            if not tag.isIFD():
                if tag.value in tags_to_redact:
                    redact_one_tag(ifd, tag, tags_to_redact[tag.value])
            else:
                # tag_info['ifds'] contains a list of lists
                # see tifftools.read_tiff
                for sub_ifds in tag_info["ifds"]:
                    redact_tiff_tags(sub_ifds, tags_to_redact)


def redact_one_image(tiff_info: TiffInfo, output_path: Path) -> None:
    ifds = tiff_info["ifds"]
    tags_to_redact = get_tags_to_redact()
    redact_tiff_tags(ifds, tags_to_redact)
    tifftools.write_tiff(tiff_info, output_path)


def get_output_path(file_path: Path, output_dir: Path) -> Path:
    return output_dir / f"REDACTED_{file_path.name}"


def redact_images(image_dir: Path, output_dir: Path) -> None:
    for child in image_dir.iterdir():
        try:
            tiff_info: TiffInfo = tifftools.read_tiff(child)
        except tifftools.TifftoolsError:
            print(f"Could not open {child.name} as a tiff. Skipping...")
            continue
        print(f"Redacting {child.name}...")
        redact_one_image(tiff_info, get_output_path(child, output_dir))


def is_directory(cli_argument: str) -> Path:
    path = Path(cli_argument).resolve()
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"{cli_argument} is not a directory")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="Image DePHI",
        description="A CLI for redacting whole slide microscopy images",
    )
    parser.add_argument("input_dir", help="Directory of images to redact", type=is_directory)
    parser.add_argument("output_dir", help="Directory to store redacted images", type=is_directory)
    args = parser.parse_args()
    redact_images(args.input_dir, args.output_dir)
    print("Done!")
