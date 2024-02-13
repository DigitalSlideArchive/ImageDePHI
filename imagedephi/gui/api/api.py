from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING
import urllib.parse

from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket

import imagedephi.gui.app
from imagedephi.gui.utils.directory import DirectoryData
from imagedephi.gui.utils.image import get_image_response_from_ifd
from imagedephi.redact import redact_images
from imagedephi.utils.progress_log import get_next_progress_message
from imagedephi.utils.tiff import get_associated_image_svs, get_ifd_for_thumbnail, get_is_svs

if TYPE_CHECKING:
    from tifftools.tifftools import IFD

router = APIRouter()


@router.get("/directory/")
def select_directory(
    directory: str = ("/"),
):
    directory_path = Path(directory)
    # TODO: if input_directory is specified but an empty string, it gets instantiated as the CWD
    if not directory_path.is_dir():
        raise HTTPException(status_code=404, detail="Input directory not a directory")

    def image_url(path: str, key: str) -> str:
        params = {"file_name": str(directory_path / path), "image_key": key}
        return "image/?" + urllib.parse.urlencode(params, safe="")

    return (
        {
            "directory_data": DirectoryData(directory_path),
            "image_url": image_url,
        },
    )


@router.get("/image/")
def get_associated_image(file_name: str = "", image_key: str = ""):
    if not file_name:
        raise HTTPException(status_code=400, detail="file_name is a required parameter")

    if image_key not in ["macro", "label", "thumbnail"]:
        raise HTTPException(
            status_code=400,
            detail=f"{image_key} is not a supported associated image key for {file_name}.",
        )
    ifd: IFD | None = None
    if image_key == "thumbnail":
        ifd = get_ifd_for_thumbnail(Path(file_name))
        if not ifd:
            raise HTTPException(
                status_code=404, detail=f"Could not generate thumbnail image for {file_name}"
            )
        return get_image_response_from_ifd(ifd, file_name)

    # image key is one of "macro", "label"
    if not get_is_svs(Path(file_name)):
        raise HTTPException(
            status_code=404, detail=f"Image key {image_key} is not supported for {file_name}"
        )

    ifd = get_associated_image_svs(Path(file_name), image_key)
    if not ifd:
        raise HTTPException(status_code=404, detail=f"No {image_key} image found for {file_name}")
    return get_image_response_from_ifd(ifd, file_name)


@router.post("/redact/")
def redact(
    input_directory: str,  # noqa: B008
    output_directory: str,  # noqa: B008
    background_tasks: BackgroundTasks,
):
    input_path = Path(input_directory)
    output_path = Path(output_directory)
    if not input_path.is_dir():
        raise HTTPException(status_code=404, detail="Input directory not found")
    if not output_path.is_dir():
        raise HTTPException(status_code=404, detail="Output directory not found")

    redact_images(input_path, output_path)

    # Shutdown after the response is sent, as this is the terminal endpoint
    background_tasks.add_task(imagedephi.gui.app.shutdown_event.set)  # type: ignore[attr-defined]


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        message = get_next_progress_message()
        if message is not None:
            message_dict = dict(count=message[0], max=message[1])
            await websocket.send_json(message_dict)
        else:
            await asyncio.sleep(0.001)
