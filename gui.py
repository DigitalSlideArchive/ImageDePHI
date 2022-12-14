import pathlib

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")


# http://localhost:8000/select-directory/?path=/home/local&foo=bar
# http://localhost:8000/?path=/home/local/KHQ/mary.salvi/projects/ImageDePHI

@app.get("/", response_class=HTMLResponse)
def select_directory(request: Request, path:str='/'):
    base_path = pathlib.Path(path)
    # TODO: what if "path" is invalid / nonexistant?
    # TODO: what about going back up (i.e. "..")? breadcrumbs!
    # TODO: how do they select their terminal directory?
    # "list comprehension"

    bread_crumbs = base_path.parts

    directory_paths = [
        path_element for path_element in base_path.iterdir() if path_element.is_dir()
    ]
    return templates.TemplateResponse(
        "sample.html.j2", {"request": request, "directory_paths": directory_paths, "bread_crumbs": bread_crumbs}
    )
