from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from http import client
import importlib.resources
from io import BytesIO
import os
from pathlib import Path
from typing import TYPE_CHECKING
import urllib.parse

from PIL import Image, UnidentifiedImageError
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
import tifftools

from imagedephi.redact import iter_image_files, redact_images
from imagedephi.utils.progress_log import get_next_progress_message

# from imagedephi.redact.redact import output_file_counter
from imagedephi.utils.tiff import get_associated_image_svs, get_ifd_for_thumbnail, get_is_svs

if TYPE_CHECKING:
    from tifftools.tifftools import IFD

MAX_ASSOCIATED_IMAGE_HEIGHT = 160


def _load_template(template_name: str) -> str | None:
    template_file = importlib.resources.files("imagedephi") / "templates" / template_name
    return template_file.read_text() if template_file.is_file() else None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Reset server state on startup, to support unit testing
    shutdown_event.clear()
    app.state.last_exception = None

    yield

    if app.state.last_exception is not None:
        # This will cause a "lifespan.shutdown.failed" event to be sent. Hypercorn will re-raise
        # this from "serve", allowing exceptions to propagate to the top level.
        raise app.state.last_exception  # pyright: ignore [reportGeneralTypeIssues]


debug_mode = eval(str(os.environ.get("DEBUG")))

app = FastAPI(
    lifespan=lifespan,
    # End users don't need access to the OpenAPI spec
    openapi_url="/openapi.json" if debug_mode else None,
    # FastAPI's debug flag will render exception tracebacks
    debug=debug_mode,
)

if debug_mode:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

else:
    app.mount(
        "/",
        StaticFiles(
            directory=str(importlib.resources.files("imagedephi") / "web_static"), html=True
        ),
        name="home",
    )
    app.mount(
        "/assets",
        StaticFiles(
            directory=str(importlib.resources.files("imagedephi") / "web_static" / "assets")
        ),
        name="assets",
    )


shutdown_event = asyncio.Event()


class DirectoryData:
    directory: Path
    ancestors: list[dict[str, str | Path]]
    child_directories: list[dict[str, str | Path]]
    child_images: list[dict[str, str | Path]]

    def __init__(self, directory: Path):
        self.directory = directory

        self.ancestors = [
            {"name": ancestor.name, "path": ancestor} for ancestor in reversed(directory.parents)
        ]
        self.ancestors.append({"name": directory.name, "path": directory})

        self.child_directories = [
            {"name": child.name, "path": child}
            for child in directory.iterdir()
            if child.is_dir() and os.access(child, os.R_OK)
        ]

        self.child_images = [
            {"name": image.name, "path": image} for image in list(iter_image_files(directory))
        ]


def extract_thumbnail_from_image_bytes(ifd: IFD, file_name: str) -> Image.Image | None:
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


def get_image_response_from_ifd(ifd: IFD, file_name: str):
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


# This exception handler not be used when FastAPI debug flag is enabled,
# due to how ServerErrorMiddleware works.
@app.exception_handler(500)
def on_internal_error(request: Request, exc: Exception) -> PlainTextResponse:
    """Return an error response and schedule the server for immediate shutdown."""
    # Unlike the default error response, this also shuts down the server.
    # A desktop application doesn't need to continue running through internal errors, and
    # continuing to run makes it harder for users and the test environment to detect fatal errors.
    app.state.last_exception = exc
    return PlainTextResponse(
        "Internal Server Error", status_code=500, background=BackgroundTask(shutdown_event.set)
    )


@app.get("/directory/")
def select_directory(
    directory: str = "/",  # noqa: B008
):
    directory_path = Path(directory)
    # TODO: if input_directory is specified but an empty string, it gets instantiated as the CWD
    if not directory_path.is_dir():
        raise HTTPException(status_code=404, detail="Input directory not a directory")

    def image_url(path: str, key: str) -> str:
        params = {"file_name": str(directory_path / path), "image_key": key}
        return "image/?" + urllib.parse.urlencode(params, safe="")

    return (
        {
            "directory_data": DirectoryData(directory_path),
            "image_url": image_url,
            "redacted": False,
        },
    )


@app.get("/image/")
def get_associated_image(file_name: str = "", image_key: str = ""):
    if not file_name:
        raise HTTPException(status_code=400, detail="file_name is a required parameter")

    if image_key not in ["macro", "label", "thumbnail"]:
        raise HTTPException(
            status_code=400,
            detail=f"{image_key} is not a supported associated image key for {file_name}.",
        )
    ifd: IFD | None = None
    if image_key == "thumbnail":
        ifd = get_ifd_for_thumbnail(Path(file_name))
        if not ifd:
            raise HTTPException(
                status_code=404, detail=f"Could not generate thumbnail image for {file_name}"
            )
        return get_image_response_from_ifd(ifd, file_name)

    # image key is one of "macro", "label"
    if not get_is_svs(Path(file_name)):
        raise HTTPException(
            status_code=404, detail=f"Image key {image_key} is not supported for {file_name}"
        )

    ifd = get_associated_image_svs(Path(file_name), image_key)
    if not ifd:
        raise HTTPException(status_code=404, detail=f"No {image_key} image found for {file_name}")
    return get_image_response_from_ifd(ifd, file_name)


@app.post("/redact/")
def redact(
    input_directory: str,  # noqa: B008
    output_directory: str,  # noqa: B008
    background_tasks: BackgroundTasks,
):
    input_path = Path(input_directory)
    output_path = Path(output_directory)
    if not input_path.is_dir():
        raise HTTPException(status_code=404, detail="Input directory not found")
    if not output_path.is_dir():
        raise HTTPException(status_code=404, detail="Output directory not found")

    redact_images(input_path, output_path)

    # Shutdown after the response is sent, as this is the terminal endpoint
    background_tasks.add_task(shutdown_event.set)
    # Should this return anything?


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        message = get_next_progress_message()
        if message is not None:
            message_dict = dict(count=message[0], max=message[1])
            await websocket.send_json(message_dict)
        else:
            await asyncio.sleep(0.001)
