from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import importlib.resources
from io import BytesIO
import os
from pathlib import Path
from typing import TYPE_CHECKING, Literal
import urllib.parse

from PIL import Image
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from jinja2 import FunctionLoader
from starlette.background import BackgroundTask
import tifftools

from imagedephi.redact import iter_image_files, redact_images
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
):
    # TODO: if input_directory is specified but an empty string, it gets instantiated as the CWD
    if not input_directory.is_dir():
        raise HTTPException(status_code=404, detail="Input directory not a directory")
    if not output_directory.is_dir():
        raise HTTPException(status_code=404, detail="Output directory not a directory")

    def image_url(path: str, key: str) -> str:
        params = {
            "file_name": str(input_directory / path),
            "image_key": key
        }
        return "image/?" + urllib.parse.urlencode(params, safe="")

    return templates.TemplateResponse(
        "DirectorySelector.html.j2",
        {
            "request": request,
            "input_directory_data": DirectoryData(input_directory),
            "output_directory_data": DirectoryData(output_directory),
            "image_url": image_url,
        },
    )


def get_image_response_from_ifd(ifd: IFD):
    # use tifftools and PIL to create a jpeg of the associated image, sized for the browser
    tiff_buffer = BytesIO()
    jpeg_buffer = BytesIO()
    tifftools.write_tiff(ifd, tiff_buffer)
    image = Image.open(tiff_buffer)

    scale_factor = MAX_ASSOCIATED_IMAGE_HEIGHT / image.size[1]
    new_size = (int(image.size[0] * scale_factor), int(image.size[1] * scale_factor))
    image.thumbnail(new_size, Image.LANCZOS)
    image.save(jpeg_buffer, "JPEG")
    jpeg_buffer.seek(0)

    # return an image response
    return StreamingResponse(jpeg_buffer, media_type="image/jpeg")


@app.get("/image/")
def get_associated_image(file_name: str = "", image_key: str = ""):
    print(f"file_name: {file_name}, image_key: {image_key}")
    if not file_name:
        return HTTPException(status_code=400, detail="file_name is a required parameter")

    if image_key not in ["macro", "label", "thumbnail"]:
        return HTTPException(status_code=400, detail=f"{image_key} is not a supported associated image key for {file_name}.")

    if image_key == "thumbnail":
        print("thumbnail")
        ifd: IFD | None = get_ifd_for_thumbnail(Path(file_name))
        if not ifd:
            return HTTPException(status_code=404, detail=f"Could not generate thumbnail image for {file_name}")
        return get_image_response_from_ifd(ifd)

    # image key is one of "macro", "label"
    if not get_is_svs(Path(file_name)):
        return HTTPException(status_code=404, detail=f"Image key {image_key} is not supported to {file_name}")

    ifd: IFD | None = get_associated_image_svs(Path(file_name), image_key)
    if not ifd:
        return HTTPException(status_code=404, detail=f"No {image_key} image found for {file_name}")
    return get_image_response_from_ifd(ifd)


@app.post("/redact/")
def redact(
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
    return {
        "message": (
            f"You chose this input directory: {input_directory} "
            f"and this output directory: {output_directory}"
        )
    }
