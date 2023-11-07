from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import importlib.resources
from io import BytesIO
import logging
import os
from pathlib import Path
from queue import Queue
import urllib.parse

from PIL import Image, UnidentifiedImageError
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request, WebSocket
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import FunctionLoader
from starlette.background import BackgroundTask
import tifftools

from imagedephi.redact import iter_image_files, redact as redact_module, redact_images

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


debug_mode = bool(os.environ.get("DEBUG"))

app = FastAPI(
    lifespan=lifespan,
    # End users don't need access to the OpenAPI spec
    openapi_url="/openapi.json" if debug_mode else None,
    # FastAPI's debug flag will render exception tracebacks
    debug=debug_mode,
)

templates = Jinja2Templates(
    # Jinja2Templates requires a "directory" argument, but it is effectively unused
    # if a custom loader is passed
    directory="",
    loader=FunctionLoader(_load_template),
)

shutdown_event = asyncio.Event()

app.mount("/assets", StaticFiles(directory="imagedephi/assets"), name="assets")
app.mount("/js", StaticFiles(directory="imagedephi/js"), name="js")


class DirectoryData:
    directory: Path
    ancestors: list[Path]
    child_directories: list[Path]
    child_images: list[Path]

    def __init__(self, directory: Path):
        self.directory = directory

        self.ancestors = list(reversed(directory.parents))
        self.ancestors.append(directory)

        self.child_directories = [
            child for child in directory.iterdir() if child.is_dir() and os.access(child, os.R_OK)
        ]

        self.child_images = list(iter_image_files(directory))


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


@app.get("/", response_class=HTMLResponse)
def select_directory(
    request: Request,
    input_directory: Path = Path("/"),  # noqa: B008
    output_directory: Path = Path("/"),  # noqa: B008
    modal="",
):
    # TODO: if input_directory is specified but an empty string, it gets instantiated as the CWD
    if not input_directory.is_dir():
        raise HTTPException(status_code=404, detail="Input directory not a directory")
    if not output_directory.is_dir():
        raise HTTPException(status_code=404, detail="Output directory not a directory")

    def image_url(path: str, key: str) -> str:
        params = {"file_name": str(input_directory / path), "image_key": key}
        return "image/?" + urllib.parse.urlencode(params, safe="")

    return templates.TemplateResponse(
        "HomePage.html.j2",
        {
            "request": request,
            "input_directory_data": DirectoryData(input_directory),
            "output_directory_data": DirectoryData(output_directory),
            "image_url": image_url,
            "modal": modal,
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
    request: Request,
    background_tasks: BackgroundTasks,
    input_directory: Path = Form(),  # noqa: B008
    output_directory: Path = Form(),  # noqa: B008
):

    if not input_directory.is_dir():
        raise HTTPException(status_code=404, detail="Input directory not found")
    if not output_directory.is_dir():
        raise HTTPException(status_code=404, detail="Output directory not found")

    redact_images(input_directory, output_directory)

    # Shutdown after the response is sent, as this is the terminal endpoint
    background_tasks.add_task(shutdown_event.set)
    return templates.TemplateResponse(
        "HomePage.html.j2",
        {
            "request": request,
            "input_directory_data": DirectoryData(input_directory),
            "output_directory_data": DirectoryData(output_directory),
            "redacted": True,
        },
    )


# The following is websockets 'hello world' testing DO NOT MERGE with this still here

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

# Not sure if this should be a generator
def progress_logging(log_queue: Queue) -> logging.LogRecord | None:
    if log_queue.not_empty:
        return log_queue.get().getMessage()


@app.get("/websocket")
async def get():
    return HTMLResponse(html)


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    redact_module.output_file_counter = 1
    await websocket.accept()
    while True:
        if redact_module.ql.not_empty:
            await websocket.send_text(f"log: {progress_logging(redact_module.ql)}")
            await asyncio.sleep(.25)
