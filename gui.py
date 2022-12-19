import pathlib

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def select_directory(request: Request, path:str='/'):
    base_path = pathlib.Path(path)

    if not base_path.exists():
        raise HTTPException(status_code=404, detail="Directory not found")

    bread_crumbs = [
        path for path in reversed(base_path.parents)
    ]
    bread_crumbs.append(base_path)

    directories = [
        path_element for path_element in base_path.iterdir() if path_element.is_dir()
    ]

    return templates.TemplateResponse(
        "DirectorySelector.html.j2", {"request": request, "directories": directories, "bread_crumbs": bread_crumbs}
    )
@app.post("/directory_selection/")
def selection(directory:str= Form()):
    return { "message": "You chose this directory: %s" %directory }
