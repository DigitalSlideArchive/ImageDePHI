import pathlib

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory=pathlib.Path(__file__).parent / "templates")


@app.get("/", response_class=HTMLResponse)
def select_directory(request: Request, path: pathlib.Path = pathlib.Path("/")):  # noqa: B008

    if not path.is_dir():
        raise HTTPException(status_code=404, detail="Not a directory")

    bread_crumbs = list(reversed(path.parents))
    bread_crumbs.append(path)

    directories = [path_element for path_element in path.iterdir() if path_element.is_dir()]

    return templates.TemplateResponse(
        "DirectorySelector.html.j2",
        {"request": request, "directories": directories, "bread_crumbs": bread_crumbs},
    )


@app.post("/directory_selection/")
def selection(directory: pathlib.Path = Form()):  # noqa: B008
    if not directory.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    return {"message": "You chose this directory: %s" % directory}
