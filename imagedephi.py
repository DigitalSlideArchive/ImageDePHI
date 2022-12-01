import argparse
from enum import Enum
from pathlib import Path
import sys
from typing import Dict, List

import tifftools
from tifftools import Datatype, TiffTag


class RedactMethod(Enum):
    REPLACE = 1
    DELETE = 2


def get_tags_to_redact() -> Dict[int, Dict]:
    return {
        270: {
            'id': 270,
            'name': 'ImageDescription',
            'method': RedactMethod.REPLACE,
            'replace_value': 'Redacted by ImageDePHI',
        }
    }


def redact_one_tag(ifd: Dict, tag: TiffTag, redact_instructions: Dict) -> None:
    if redact_instructions['method'] == RedactMethod.REPLACE:
        ifd['tags'][tag.value]['data'] = redact_instructions['replace_value']
    elif redact_instructions['method'] == RedactMethod.DELETE:
        del ifd['tags'][tag.value]


def redact_tiff_tags(ifds: List[Dict], tags_to_redact: Dict[int, Dict]) -> None:
    for ifd in ifds:
        sub_ifd_list = []
        for tag, tag_info in sorted(ifd['tags'].items()):
            tag = tifftools.commands.get_or_create_tag(
                tag,
                tifftools.Tag,
                {'datatype': Datatype[tag_info['datatype']]},
            )
            if not tag.isIFD():
                if tag.value in tags_to_redact:
                    redact_one_tag(ifd, tag, tags_to_redact[tag.value])
            else:
                sub_ifd_list.append((tag, tag_info))
                # tag_info['ifds'] contains a list of lists
                # see tifftools.read_tiff
                for sub_ifds in tag_info['ifds']:
                    redact_tiff_tags(sub_ifds, tags_to_redact)


def redact_one_image(tiff_info: Dict, output_path: Path) -> None:
    ifds = tiff_info['ifds']
    tags_to_redact = get_tags_to_redact()
    redact_tiff_tags(ifds, tags_to_redact)
    tifftools.write_tiff(tiff_info, output_path)


def get_output_path(file_path: Path, output_dir: Path) -> Path:
    return output_dir / f'REDACTED_{file_path.name}'


def redact_images(image_dir: Path, output_dir: Path) -> None:
    for child in image_dir.iterdir():
        try:
            tiff_info = tifftools.read_tiff(child)
        except tifftools.exceptions.TifftoolsError:
            print(f'Could not open {child.name} as a tiff. Skipping...')
            continue
        print(f'Redacting {child.name}...')
        redact_one_image(tiff_info, get_output_path(child, output_dir))


def main():
    parser = argparse.ArgumentParser(
        prog='Image DePHI',
        description='A CLI for redacting whole slide microscopy images',
    )
    parser.add_argument(
        'input_dir',
        help='Directory of images to redact',
        type=Path,
    )
    parser.add_argument('output_dir', help='Directory to store redacted images', type=Path)
    args = parser.parse_args()
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    if not input_dir.is_dir():
        print('Input directory must be a directory')
        sys.exit(1)
    if not output_dir.is_dir():
        print('Output directory must be a directory')
        sys.exit(1)
    redact_images(input_dir, output_dir)
    print('Done!')


if __name__ == '__main__':
    main()
