from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import importlib.resources
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import FunctionLoader
from starlette.background import BackgroundTask

from imagedephi.redact import iter_image_files, redact_images


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


app = FastAPI(lifespan=lifespan)
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

        self.child_directories = [child for child in directory.iterdir() if child.is_dir()]

        self.child_images = list(iter_image_files(directory))


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


@app.get("/", response_class=RedirectResponse)
def home(request: Request) -> str:
    # On Windows, there may be multiple roots, so pick the one that's an ancestor of the CWD
    # On Linux, this should typically resolve to "/"
    root_directory = Path.cwd().root

    # TODO: FastAPI has a bug where a URL object can't be directly returned here
    return str(
        request.url_for("select_directory").include_query_params(
            input_directory=str(root_directory), output_directory=str(root_directory)
        )
    )


@app.get("/select-directory", response_class=HTMLResponse)
def select_directory(
    request: Request,
    input_directory: Path,
    output_directory: Path,
) -> Response:
    # TODO: if input_directory is specified but an empty string, it gets instantiated as the CWD
    if not input_directory.is_dir():
        raise HTTPException(status_code=404, detail="Input directory not a directory")
    if not output_directory.is_dir():
        raise HTTPException(status_code=404, detail="Output directory not a directory")

    return templates.TemplateResponse(
        "DirectorySelector.html.j2",
        {
            "request": request,
            "input_directory_data": DirectoryData(input_directory),
            "output_directory_data": DirectoryData(output_directory),
        },
    )


@app.post("/redact", response_class=HTMLResponse)
def redact(
    background_tasks: BackgroundTasks,
    input_directory: Path = Form(),  # noqa: B008
    output_directory: Path = Form(),  # noqa: B008
) -> str:
    if not input_directory.is_dir():
        raise HTTPException(status_code=404, detail="Input directory not found")
    if not output_directory.is_dir():
        raise HTTPException(status_code=404, detail="Output directory not found")

    redact_images(input_directory, output_directory)

    # Shutdown after the response is sent, as this is the terminal endpoint
    background_tasks.add_task(shutdown_event.set)
    return (
        f"You chose this input directory: {input_directory} "
        f"and this output directory: {output_directory}"
    )
