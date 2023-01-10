import pathlib

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory=pathlib.Path(__file__).parent / "templates")


@app.get("/", response_class=HTMLResponse)
def select_directory(request: Request, path: str = "/"):
    base_path = pathlib.Path(path)

    if not base_path.exists():
        raise HTTPException(status_code=404, detail="Directory not found")

    if not base_path.is_dir():
        raise HTTPException(status_code=404, detail="Not a directory")

    bread_crumbs = list(reversed(base_path.parents))
    bread_crumbs.append(base_path)

    directories = [path_element for path_element in base_path.iterdir() if path_element.is_dir()]

    return templates.TemplateResponse(
        "DirectorySelector.html.j2",
        {"request": request, "directories": directories, "bread_crumbs": bread_crumbs},
    )


@app.post("/directory_selection/")
def selection(directory: str = Form()):  # noqa: B008
    selection = pathlib.Path(directory)
    if not selection.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    return {"message": "You chose this directory: %s" % selection}
