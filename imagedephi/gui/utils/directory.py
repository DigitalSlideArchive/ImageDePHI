import os
from pathlib import Path

from imagedephi.redact import iter_image_files


class DirectoryData:
    directory: Path
    ancestors: list[dict[str, str | Path]]
    child_directories: list[dict[str, str | Path]]
    child_images: list[dict[str, str | Path]]

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
            {"name": image.name, "path": image} for image in list(iter_image_files(directory))
        ]
