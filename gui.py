import pathlib

from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def select_directory(request: Request, path:str='/'):
    base_path = pathlib.Path(path)

    bread_crumbs = base_path.parts
    if not base_path.exists():
        raise HTTPException(status_code=404, detail="Directory not found")

    directory_paths = [
        path_element for path_element in base_path.iterdir() if path_element.is_dir()
    ]

    return templates.TemplateResponse(
        "sample.html.j2", {"request": request, "directory_paths": directory_paths, "bread_crumbs": bread_crumbs}
    )
@app.post("/directory_selection/")
def selection(directory:str= Form()):
    return { "message": "You chose this directory: %s" %directory }
