from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
import errno
import importlib.resources
import io
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import FunctionLoader

from imagedephi.redact import iter_image_files, redact_images


def _load_template(template_name: str) -> str | None:
    template_file = importlib.resources.files("imagedephi") / "templates" / template_name
    return template_file.read_text() if template_file.is_file() else None


app = FastAPI()
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


@app.on_event("startup")
def reset_shutdown_event() -> None:
    # Important for unit testing, to reset the server state
    shutdown_event.clear()


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

    return templates.TemplateResponse(
        "DirectorySelector.html.j2",
        {
            "request": request,
            "input_directory_data": DirectoryData(input_directory),
            "output_directory_data": DirectoryData(output_directory),
        },
    )


@app.post("/redact/")
def redact(
    background_tasks: BackgroundTasks,
    input_directory: Path = Form(),  # noqa: B008
    output_directory: Path = Form(),  # noqa: B008
    overwrite: bool = Form(),
):
    if not input_directory.is_dir():
        raise HTTPException(status_code=404, detail="Input directory not found")
    if not output_directory.is_dir():
        raise HTTPException(status_code=404, detail="Output directory not found")

    if overwrite:
        redact_images(input_directory, output_directory, overwrite=True)
        # I think this goes here too
        background_tasks.add_task(shutdown_event.set)
        return {"message": "Image(s) successfully overwritten"}

    # Should we handle other failures?
    elif redact_images(input_directory, output_directory) == errno.EEXIST:
        return templates.TemplateResponse(
            "SelectedDirectory.html.j2",
            {
                "request": request,
                "input_directory": input_directory,
                "output_directory": output_directory,
            },
        )

    else:
        # Shutdown after the response is sent, as this is the terminal endpoint
        background_tasks.add_task(shutdown_event.set)
        return {
            "message": (
                f"You chose this input directory: {input_directory} "
                f"and this output directory: {output_directory}"
            )
        }
