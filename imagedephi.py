import argparse
from enum import Enum
from pathlib import Path

import tifftools
from tifftools import Datatype


class RedactMethod(Enum):
    REPLACE = 1
    DELETE = 2


def get_tags_to_redact():
    return {
        270: {
            'id': 270,
            'name': 'ImageDescription',
            'method': RedactMethod.REPLACE,
            'replace_value': 'Redacted by ImageDePHI'
        }
    }


def redact_one_tag(ifd, tag, redact_instructions):
    if redact_instructions['method'] == RedactMethod.REPLACE:
        ifd['tags'][tag.value]['data'] = redact_instructions['replace_value']
    elif redact_instructions['method'] == RedactMethod.DELETE:
        del ifd['tags'][tag.value]


def redact_tiff_tags(ifds, tags_to_redact):
    for ifd in ifds:
        sub_ifd_list = []
        for tag, tag_info in sorted(ifd['tags'].items()):
            tag = tifftools.commands.get_or_create_tag(
                tag,
                tifftools.Tag,
                {'datatype': Datatype[tag_info['datatype']]},
            )
            if not tag.isIFD() and tag_info['datatype'] not in (
                Datatype.IFD,
                Datatype.IFD8,
            ):
                if tag.value in tags_to_redact.keys():
                    redact_one_tag(ifd, tag, tags_to_redact[tag.value])
            else:
                sub_ifd_list.append((tag, tag_info))
        for tag, tag_info in sub_ifd_list:
            for sub_ifds in tag_info['ifds']:
                redact_tiff_tags(sub_ifds, tags_to_redact)


def redact_one_image(image_path):
    tiff_info = tifftools.read_tiff(image_path)
    ifds = tiff_info['ifds']
    tags_to_redact = get_tags_to_redact()
    redact_tiff_tags(ifds, tags_to_redact)
    output_image_path = (
        str(image_path.parent) + '/REDACTED_' + str(image_path.name)
    )
    tifftools.write_tiff(tiff_info, output_image_path)


def main():
    parser = argparse.ArgumentParser(
        prog="Image DePHI",
        description="A CLI for redacting whole slide microscopy images",
    )
    parser.add_argument("image", help="Path to the image file to be redacted")
    args = parser.parse_args()
    image_path = Path(args.image).resolve()
    redact_one_image(image_path)


if __name__ == "__main__":
    main()
