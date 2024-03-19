from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image, UnidentifiedImageError
from fastapi.responses import StreamingResponse
import tifftools

from imagedephi.gui.utils.constants import MAX_ASSOCIATED_IMAGE_HEIGHT

if TYPE_CHECKING:
    from tifftools.tifftools import IFD


def extract_thumbnail_from_image_bytes(ifd: "IFD", file_name: str) -> Image.Image | None:
    offsets = ifd["tags"][tifftools.Tag.TileOffsets.value]["data"]
    byte_counts = ifd["tags"][tifftools.Tag.TileByteCounts.value]["data"]
    num_tiles = len(offsets)

    height = int(ifd["tags"][tifftools.Tag.ImageLength.value]["data"][0])
    width = int(ifd["tags"][tifftools.Tag.ImageWidth.value]["data"][0])
    top: int = 0
    left: int = 0

    image_canvas: Image.Image | None = None
    with open(file_name, "rb") as image_file:
        for idx in range(num_tiles):
            image_file.seek(int(offsets[idx]))
            tile_bytes = BytesIO(image_file.read(int(byte_counts[idx])))
            tile_image = Image.open(tile_bytes)

            if not image_canvas:
                image_canvas = Image.new(tile_image.mode, (width, height))

            tile_size = tile_image.size

            bottom = top + tile_size[0]
            right = left + tile_size[1]
            if bottom > height:
                bottom = height
            if right > width:
                right = width

            piece_height = bottom - top
            piece_width = right - left

            if piece_width != tile_image.size[1] or piece_height != tile_image.size[0]:
                tile_image = tile_image.crop((0, 0, piece_width, piece_height))

            image_canvas.paste(tile_image, (left, top, right, bottom))

            left = right
            if left >= width:
                # go to next row
                left = 0
                top = top + tile_size[0]

    if not image_canvas:
        return None

    scale_factor = MAX_ASSOCIATED_IMAGE_HEIGHT / image_canvas.size[1]
    new_size = (
        int(image_canvas.size[0] * scale_factor),
        int(image_canvas.size[1] * scale_factor),
    )
    resized_image = image_canvas.resize(new_size, Image.LANCZOS)
    return resized_image


def get_image_response_from_ifd(ifd: "IFD", file_name: str):
    # use tifftools and PIL to create a jpeg of the associated image, sized for the browser
    tiff_buffer = BytesIO()
    jpeg_buffer = BytesIO()
    tifftools.write_tiff(ifd, tiff_buffer)
    try:
        image = Image.open(tiff_buffer)

        scale_factor = MAX_ASSOCIATED_IMAGE_HEIGHT / image.size[1]
        new_size = (int(image.size[0] * scale_factor), int(image.size[1] * scale_factor))
        image.thumbnail(new_size, Image.LANCZOS)
        image.save(jpeg_buffer, "JPEG")
        jpeg_buffer.seek(0)

        # return an image response
        return StreamingResponse(jpeg_buffer, media_type="image/jpeg")
    except UnidentifiedImageError:
        #  Extract a thumbnail from the original image if the IFD can't be opened by PIL
        composite_image = extract_thumbnail_from_image_bytes(ifd, file_name)
        if composite_image:
            composite_image.save(jpeg_buffer, "JPEG")
            jpeg_buffer.seek(0)
            return StreamingResponse(jpeg_buffer, media_type="image/jpeg")
