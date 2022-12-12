from pathlib import Path

import tifftools

import imagedephi


def verify_redaction_one_tag(ifd, tag, rule):
    if rule['method'] == imagedephi.RedactMethod.REPLACE:
        assert ifd['tags'][tag.value]['data'] == rule['replace_value']
    elif rule['method'] == imagedephi.RedactMethod.DELETE:
        assert tag.value not in ifd['tags']


def verify_redaction(ifds, rules):
    for ifd in ifds:
        for tag, tag_info in ifd['tags'].items():
            tiff_tag = tifftools.constants.get_or_create_tag(
                tag, tifftools.Tag, datatype=tifftools.Datatype[tag_info['datatype']]
            )
            if not tiff_tag.isIFD():
                if tiff_tag.value in rules:
                    verify_redaction_one_tag(ifd, tiff_tag, rules[tiff_tag.value])
            else:
                for sub_ifds in tag_info['ifds']:
                    verify_redaction(sub_ifds, rules)


def test_redact_images(tmp_path, mocker):
    redact_one_image_spy = mocker.spy(imagedephi, 'redact_one_image')
    input_dir = Path(__file__).parent / 'data' / 'input'
    output_dir = tmp_path / 'output'
    output_dir.mkdir()
    imagedephi.redact_images(input_dir, output_dir)

    assert redact_one_image_spy.call_count == 1

    # ensure that each output file is properly redacted
    for output_file in output_dir.iterdir():
        tiff_info = tifftools.read_tiff(output_file)
        verify_redaction(tiff_info['ifds'], imagedephi.get_tags_to_redact())
