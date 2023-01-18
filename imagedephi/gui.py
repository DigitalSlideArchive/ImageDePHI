from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


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

    input_directories = [
        path_element for path_element in input_directory.iterdir() if path_element.is_dir()
    ]
    output_directories = [
        path_element for path_element in output_directory.iterdir() if path_element.is_dir()
    ]

    return templates.TemplateResponse(
        "DirectorySelector.html.j2",
        {
            "request": request,
            "input_directories": input_directories,
            "output_directories": output_directories,
            "input_bread_crumbs": input_bread_crumbs,
            "output_bread_crumbs": output_bread_crumbs,
            "current_input": input_directory,
            "current_output": output_directory,
        },
    )


@app.post("/directory_selection/")
def selection(input_directory: Path = Form(), output_directory: Path = Form()):  # noqa: B008
    if not input_directory.is_dir():
        raise HTTPException(status_code=404, detail="Input directory not found")
    if not output_directory.is_dir():
        raise HTTPException(status_code=404, detail="Output directory not found")

    return {
        "message": "You chose this input directory: %s and this output directory: %s"
        % (input_directory, output_directory)
    }
