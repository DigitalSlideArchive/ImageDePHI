from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import List

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from imagedephi.redact import redact_images

app = FastAPI()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

shutdown_event = asyncio.Event()


@dataclass
class DirectoryData:
    directory_path: Path
    images: List[Path]


def _create_directory_list(path: Path) -> List[DirectoryData]:
    directory_list: List[DirectoryData] = []
    for directory in path.iterdir():
        if directory.is_dir():
            children: List[Path] = []
            try:
                for child in directory.iterdir():
                    if child.suffix == ".tif" or child.suffix == ".svs":
                        children.append(child)
            except PermissionError:
                pass
            directory_list.append({"directory_path": directory, "images": children})

    return directory_list


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
    if not input_directory.is_dir():
        raise HTTPException(status_code=404, detail="Input directory not a directory")
    if not output_directory.is_dir():
        raise HTTPException(status_code=404, detail="Output directory not a directory")

    input_bread_crumbs = list(reversed(input_directory.parents))
    input_bread_crumbs.append(input_directory)

    output_bread_crumbs = list(reversed(output_directory.parents))
    output_bread_crumbs.append(output_directory)

    return templates.TemplateResponse(
        "DirectorySelector.html.j2",
        {
            "request": request,
            "input_directories": _create_directory_list(input_directory),
            "output_directories": _create_directory_list(output_directory),
            "input_bread_crumbs": input_bread_crumbs,
            "output_bread_crumbs": output_bread_crumbs,
            "current_input": input_directory,
            "current_output": output_directory,
        },
    )


@app.post("/directory_selection/")
def selection(
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
