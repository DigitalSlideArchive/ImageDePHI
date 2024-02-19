import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import importlib.resources
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from imagedephi.gui.api import api

shutdown_event = asyncio.Event()
debug_mode = eval(str(os.environ.get("DEBUG")))


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


app = FastAPI(
    lifespan=lifespan,
    # End users don't need access to the OpenAPI spec
    openapi_url="/openapi.json" if debug_mode else None,
    # FastAPI's debug flag will render exception tracebacks
    debug=debug_mode,
)

app.include_router(api.router)  # type: ignore

if debug_mode:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

else:
    app.mount(
        "/",
        StaticFiles(
            directory=str(importlib.resources.files("imagedephi") / "web_static"), html=True
        ),
        name="home",
    )
    app.mount(
        "/assets",
        StaticFiles(
            directory=str(importlib.resources.files("imagedephi") / "web_static" / "assets")
        ),
        name="assets",
    )


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
