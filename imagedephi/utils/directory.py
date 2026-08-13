from collections.abc import Generator
from pathlib import Path

from imagedephi.utils.image import get_file_format_from_path


def iter_image_files(path: Path) -> Generator[Path, None, None]:
    file_format = None
    try:
        file_format = get_file_format_from_path(path)
    except PermissionError:
        # Don't attempt to redact inaccessible files
        pass
    if file_format:
        yield path


def iter_image_dirs(paths: list[Path], recursive: bool = False) -> Generator[Path, None, None]:
    for path in paths:
        if path.is_file():
            yield from iter_image_files(path)
        elif path.is_dir() and recursive:
            yield from iter_image_dirs(sorted(path.iterdir()), recursive)
        elif path.is_dir() and not recursive:
            for child in path.iterdir():
                if child.is_file():
                    yield from iter_image_files(child)
