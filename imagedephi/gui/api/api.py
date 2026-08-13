from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional
import urllib.parse

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse

from imagedephi.redact import redact_images, show_redaction_plan
from imagedephi.rules import FileFormat
from imagedephi.utils.constants import MAX_ASSOCIATED_IMAGE_SIZE
from imagedephi.utils.dicom import file_is_same_series_as
from imagedephi.utils.directory import iter_image_dirs
from imagedephi.utils.image import (
    get_file_format_from_path,
    get_image_bytes_from_dicom,
    get_image_bytes_from_ifd,
    get_image_bytes_from_tiff,
)
from imagedephi.utils.progress_log import get_next_progress_message
from imagedephi.utils.tiff import get_associated_image_svs, get_ifd_for_thumbnail, get_is_svs

if TYPE_CHECKING:
    from tifftools.tifftools import IFD

router = APIRouter()


def _iter_yaml_files(directory: Path):
    for child in directory.iterdir():
        if child.is_file() and child.suffix == ".yaml":
            yield child


class DirectoryData:
    directory: Path
    ancestors: list[dict[str, str | Path]]
    child_directories: list[dict[str, str | Path]]
    child_images: list[dict[str, str | Path]]
    child_yaml_files: list[dict[str, str | Path]]

    def __init__(self, directory: Path):
        self.directory = directory

        self.ancestors = [
            {"name": ancestor.name, "path": ancestor} for ancestor in reversed(directory.parents)
        ]
        self.ancestors.append({"name": directory.name, "path": directory})

        self.child_directories = [
            {"name": child.name, "path": child}
            for child in directory.iterdir()
            if child.is_dir() and os.access(child, os.R_OK)
        ]

        self.child_images = [
            {"name": image.name, "path": image} for image in list(iter_image_dirs([directory]))
        ]
        self.child_yaml_files = [
            {"name": yaml_file.name, "path": yaml_file} for yaml_file in _iter_yaml_files(directory)
        ]


@router.get("/directory/")
def select_directory(
    directory: str = ("/"),
):
    directory_path = Path(directory)
    # TODO: if input_directory is specified but an empty string, it gets instantiated as the CWD
    if not directory_path.exists():
        raise HTTPException(status_code=404, detail="Input directory not found")

    def image_url(path: str, key: str) -> str:
        params = {"file_name": str(directory_path / path), "image_key": key}
        return "image/?" + urllib.parse.urlencode(params, safe="")

    return (
        {
            "directory_data": DirectoryData(directory_path),
            "image_url": image_url,
        },
    )


@router.get("/image/", response_class=FileResponse)
def get_associated_image(
    file_name: str = "",
    image_key: str = "",
    max_height=MAX_ASSOCIATED_IMAGE_SIZE,
    max_width=MAX_ASSOCIATED_IMAGE_SIZE,
):
    if not file_name:
        raise HTTPException(status_code=400, detail="file_name is a required parameter")

    if not Path(file_name).exists():
        raise HTTPException(status_code=404, detail=f"{file_name} does not exist")

    if image_key not in ["macro", "label", "thumbnail"]:
        raise HTTPException(
            status_code=400,
            detail=f"{image_key} is not a supported associated image key for {file_name}.",
        )

    image_type = get_file_format_from_path(Path(file_name))
    if image_type == FileFormat.SVS or image_type == FileFormat.TIFF:
        ifd: IFD | None = None
        if image_key == "thumbnail":
            ifd = get_ifd_for_thumbnail(Path(file_name), int(max_width), int(max_height))
            if not ifd:
                try:
                    # If the image is not tiled, no appropriate IFD was found. In this case
                    # attempt to get a thumbnail using the entire image.
                    jpeg_buffer = get_image_bytes_from_tiff(file_name, max_width, max_height)
                    return StreamingResponse(jpeg_buffer, media_type="image/jpeg")
                except Exception as e:
                    raise HTTPException(
                        status_code=422,  # unprocessable content
                        detail=f"Could not generate thumbnail image for {file_name}: {e.args[0]}",
                    )
            else:
                try:
                    jpeg_buffer = get_image_bytes_from_ifd(ifd, file_name, max_width, max_height)
                    return StreamingResponse(jpeg_buffer, media_type="image/jpeg")
                except Exception as e:
                    raise HTTPException(
                        status_code=422,  # unprocessable content
                        detail=f"Could not generate thumbnail image for {file_name}: {e.args[0]}",
                    )

        # image key is one of "macro", "label"
        if not get_is_svs(Path(file_name)):
            raise HTTPException(
                status_code=404, detail=f"Image key {image_key} is not supported for {file_name}"
            )

        ifd = get_associated_image_svs(Path(file_name), image_key)
        if not ifd:
            raise HTTPException(
                status_code=404, detail=f"No {image_key} image found for {file_name}"
            )
        try:
            return get_image_bytes_from_ifd(ifd, file_name, max_height, max_width)
        except Exception as e:
            raise HTTPException(
                status_code=422,  # unprocessable content
                detail=f"Could not generate thumbnail image for {file_name}: {e.args[0]}",
            )
    elif image_type == FileFormat.DICOM:
        path = Path(file_name)
        related_files = [
            child
            for child in path.parent.iterdir()
            if child != path and file_is_same_series_as(path, child)
        ]
        image_response = get_image_bytes_from_dicom(related_files, image_key, max_width, max_height)
        if image_response:
            return StreamingResponse(image_response, media_type="image/jpeg")
        raise HTTPException(
            status_code=404, detail=f"Could not retrieve {image_key} image for {file_name}"
        )

    return HTTPException(
        status_code=404, detail=f"Could not retrieve {image_key} image for {file_name}"
    )


@router.get("/redaction_plan")
def get_redaction_plan(
    input_directory: str = ("/"),  # noqa: B008
    rules_path: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    update: bool = True,
):
    input_path = Path(input_directory)
    if not input_path.is_dir():
        raise HTTPException(status_code=404, detail="Input directory not found")

    # TODO: Add support for multiple input directories in the UI
    if rules_path and not Path(rules_path).is_file():
        rules_path = None
        print("Rules file not found")
    if rules_path:
        return show_redaction_plan(
            [input_path], override_rules=Path(rules_path), limit=limit, offset=offset, update=update
        )._asdict()

    return show_redaction_plan([input_path], limit=limit, offset=offset, update=update)._asdict()


@router.post("/redact/")
def redact(
    input_directory: str,  # noqa: B008
    output_directory: str,  # noqa: B008
    rules_path: Optional[str] = None,
    rename: bool = True,
    export_associated: bool = False,
):
    input_path = Path(input_directory)
    output_path = Path(output_directory)
    if not input_path.is_dir():
        raise HTTPException(status_code=404, detail="Input directory not found")
    if not output_path.is_dir():
        raise HTTPException(status_code=404, detail="Output directory not found")
    if rules_path is not None and not Path(rules_path).is_file():
        rules_path = None
        print("Rules file not found")
    # TODO: Add support for multiple input directories in the UI
    if rules_path:
        redact_images(
            [input_path],
            output_path,
            override_rules=Path(rules_path),
            rename=rename,
            export_associated=export_associated,
        )
    else:
        redact_images(
            [input_path],
            output_path,
            rename=rename,
            export_associated=export_associated,
        )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    backoff = 1

    while True:
        try:
            print("Client connected")
            backoff = 1

            while True:
                message = get_next_progress_message()
                if message is not None:
                    message_dict = dict(
                        count=message[0], max=message[1], redact_dir=message[2].name
                    )
                    await websocket.send_json(message_dict)
                else:
                    await asyncio.sleep(0.001)  # Add a small delay to avoid busy waiting

        except WebSocketDisconnect:
            print("Attempting to reconnect to client")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
            await websocket.accept()
