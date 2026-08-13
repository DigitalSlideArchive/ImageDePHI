from __future__ import annotations

from collections import OrderedDict, namedtuple
from collections.abc import Generator
from csv import DictWriter
import datetime
from enum import Enum
import importlib.resources
from io import BytesIO
import logging
from pathlib import Path
from shutil import copy2
from typing import TYPE_CHECKING, Any, Dict, NamedTuple, TypeVar

from PIL import Image, ImageDraw, ImageFont
import tifftools
import tifftools.constants
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
import yaml

from imagedephi.rules import FileFormat, Ruleset
from imagedephi.utils.dicom import file_is_same_series_as
from imagedephi.utils.directory import iter_image_dirs
from imagedephi.utils.image import (
    get_file_format_from_path,
    get_image_bytes_from_dicom,
    get_image_bytes_from_ifd,
    get_image_bytes_from_tiff,
)
from imagedephi.utils.logger import logger
from imagedephi.utils.progress_log import push_progress
from imagedephi.utils.tiff import get_associated_image_svs, get_ifd_for_thumbnail

from .build_redaction_plan import build_redaction_plan
from .svs import MalformedAperioFileError
from .tiff import UnsupportedFileTypeError

if TYPE_CHECKING:
    from .redaction_plan import TagRedactionPlan

MAX_ASSOCIATED_OUTPUT_SIZE = 500

tags_used: OrderedDict[str, dict[str, Any]] = OrderedDict()
redaction_plan_report: Dict[str, Dict[str, Any]] = {}
unprocessable_image_messages: list[str] = []

T = TypeVar("T")
missing_rules = False


class ProfileChoice(Enum):
    Strict = "strict"
    Dates = "dates"
    Default = "default"


def _get_output_path(
    file_path: Path,
    output_dir: Path,
    base_name: str,
    count: int,
    max: int,
) -> Path:
    return output_dir / f"{base_name}_{count:0{len(str(max))}}{file_path.suffix}"


def _get_user_rules(override_rules: Path) -> Ruleset:
    with override_rules.open() as override_rules_stream:
        user_rule_set = Ruleset.model_validate(yaml.safe_load(override_rules_stream))
        return user_rule_set


def get_base_rules(profile: str = "") -> Ruleset:
    """
    Return the rule set associated with the given profile.

    Default to the base rules if no profile is specified.
    """
    if profile == ProfileChoice.Strict.value:
        base_rules_path = importlib.resources.files("imagedephi") / "minimum_rules.yaml"
    elif profile == ProfileChoice.Dates.value:
        base_rules_path = importlib.resources.files("imagedephi") / "modify_dates_rules.yaml"
    else:
        base_rules_path = importlib.resources.files("imagedephi") / "base_rules.yaml"

    with base_rules_path.open() as base_rules_stream:
        base_rule_set = Ruleset.parse_obj(yaml.safe_load(base_rules_stream))
        return base_rule_set


def generator_to_list_with_progress(
    generator: Generator[T, None, None], progress_bar_desc="Working..."
) -> list[T]:
    result = []
    for item in tqdm(generator, desc=progress_bar_desc, dynamic_ncols=True, unit=" image(s) found"):
        result.append(item)
    return result


def create_redact_dir_and_manifest(
    base_output_dir: Path, associated: bool, time_stamp: str
) -> tuple[Path, Path, Path]:
    """
    Create output directories and manifest file.

    `identifier` should be a unique string for the new directory. If no value
    is supplied, a timestamp is used.
    """
    redact_dir = base_output_dir / f"Redacted_{time_stamp}"
    associated_dir = base_output_dir / f"Associated_{time_stamp}"
    manifest_file = base_output_dir / f"Redacted_{time_stamp}_manifest.csv"

    try:
        redact_dir.mkdir(parents=True)
        if associated:
            associated_dir.mkdir()
        manifest_file.touch()
    except PermissionError:
        logger.error("Cannnot create an output directory, permission error.")
        raise
    else:
        logger.info(f"Created redaction folder: {redact_dir}")
        return redact_dir, associated_dir, manifest_file


def missing_image(
    text: list[str],
    size: tuple[int, int] = (300, 300),
    background: tuple[int, int, int] = (0, 0, 0),
    foreground: tuple[int, int, int] = (255, 255, 255),
    fontsize: int = 40,
) -> BytesIO:
    """Return a text images as a placeholder for missing associated images."""
    img = Image.new("RGB", size, color=background)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(fontsize)
    draw.multiline_text(
        (size[0] // 2, size[1] // 2),
        "\n".join(text),
        anchor="mm",
        font=font,
        fill=foreground,
    )
    jpeg_buffer = BytesIO()
    img.save(jpeg_buffer, "JPEG")
    jpeg_buffer.seek(0)
    return jpeg_buffer


def get_associated_outputs(
    file_name: str = "",
    max_height=MAX_ASSOCIATED_OUTPUT_SIZE,
    max_width=MAX_ASSOCIATED_OUTPUT_SIZE,
) -> dict[str, BytesIO]:
    """Return encoded JPEGs from the associated images contained in `file_name`."""
    image_type = get_file_format_from_path(Path(file_name))
    if image_type == FileFormat.SVS or image_type == FileFormat.TIFF:
        if ifd := get_associated_image_svs(Path(file_name), "label"):
            try:
                label = get_image_bytes_from_ifd(ifd, file_name, max_height, max_width)
            except Exception:
                label = missing_image(text=["label", "missing"])
        else:
            label = missing_image(text=["label", "missing"])
        ifd = get_ifd_for_thumbnail(Path(file_name), int(max_width), int(max_height))
        if not ifd:
            try:
                thumbnail = get_image_bytes_from_tiff(file_name, max_width, max_height)
            except Exception:
                thumbnail = missing_image(text=["thumbnail", "missing"])
        else:
            try:
                thumbnail = get_image_bytes_from_ifd(ifd, file_name, max_width, max_height)
            except Exception:
                thumbnail = missing_image(text=["thumbnail", "missing"])
        if ifd := get_associated_image_svs(Path(file_name), "macro"):
            try:
                macro = get_image_bytes_from_ifd(ifd, file_name, max_height, max_width)
            except Exception:
                macro = missing_image(text=["macro", "missing"])
        else:
            macro = missing_image(text=["macro", "missing"])
        return dict(label=label, thumbnail=thumbnail, macro=macro)
    elif image_type == FileFormat.DICOM:
        path = Path(file_name)
        related_files = [
            child
            for child in path.parent.iterdir()
            if child != path and file_is_same_series_as(path, child)
        ]
        try:
            label = get_image_bytes_from_dicom(related_files, "label", max_width, max_height)
        except Exception:
            label = missing_image(text=["label", "missing"])
        try:
            overview = get_image_bytes_from_dicom(related_files, "overview", max_width, max_height)
        except Exception:
            overview = missing_image(text=["overview", "missing"])
        return dict(label=label, thumbnail=overview)
    return dict()


def redact_images(
    input_paths: list[Path],
    output_dir: Path,
    override_rules: Path | None = None,
    rename: bool = True,
    profile: str = "",
    overwrite: bool = False,
    recursive: bool = False,
    export_associated: bool = False,
    index: int = 1,
) -> None:

    time_stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Keep track of information about this run to write to a persistent log file (csv?)
    # (original_name, output_name) as bare minimum
    # error message? rule set (base/override)?
    run_summary = []
    base_rules = get_base_rules(profile)
    override_ruleset = None
    if override_rules:
        override_ruleset = _get_user_rules(override_rules)
    output_file_name_base = (
        override_ruleset.output_file_name if override_ruleset else base_rules.output_file_name
    )
    images_to_redact = []

    with logging_redirect_tqdm(loggers=[logger]):
        images_to_redact += generator_to_list_with_progress(
            iter_image_dirs(input_paths, recursive),
            progress_bar_desc="Collecting files to redact...",
        )

    output_file_counter = 1
    output_file_max = len(images_to_redact)
    failed_img_counter = 0
    failed_images: dict[
        str, list[dict[str, dict[str, int | str | list[str] | TagRedactionPlan]]]
    ] = {"failed_images": []}
    redact_dir, associated_dir, manifest_file = create_redact_dir_and_manifest(
        output_dir, export_associated, time_stamp
    )
    failed_dir = output_dir / f"Failed_{time_stamp}"
    failed_manifest_file = (
        output_dir / f"Failed_{time_stamp}" / f"Failed_{time_stamp}_manifest.yaml"
    )

    dcm_uid_map: dict[str, str] = {}

    with logging_redirect_tqdm(loggers=[logger]):
        for image_file in tqdm(images_to_redact, desc="Redacting images", position=0, leave=True):
            push_progress(output_file_counter, output_file_max, redact_dir)
            try:
                redaction_plan = build_redaction_plan(
                    image_file, base_rules, override_ruleset, dcm_uid_map=dcm_uid_map
                )
            # Handle and report other errors without stopping the process
            except Exception as e:
                logger.error(
                    f"{image_file.name} could not be processed. "
                    f"{e.args[0] if len(e.args) else e}"
                )
                run_summary.append(
                    {
                        "input_path": image_file,
                        "output_path": "",
                        "detail": "There was an unexpected error when redacting this image.",
                    }
                )
                output_file_counter += 1
                continue
            if not redaction_plan.is_comprehensive():
                nested_failed_dir: Path = Path()
                logger.error(f"Redaction could not be performed for {image_file.name}.")
                failed_img_counter += 1
                if failed_img_counter == 1:
                    failed_dir.mkdir(parents=True)
                    failed_manifest_file.touch()

                if recursive:
                    if image_file.parent in input_paths:
                        failed_parent_index = input_paths.index(image_file.parent)
                    for ancestor in image_file.parents:
                        if ancestor in input_paths:
                            failed_parent_index = input_paths.index(ancestor)
                            break
                    nested_failed_dir = Path(
                        str(image_file).replace(
                            str(input_paths[failed_parent_index]), str(failed_dir), 1
                        )
                    ).parent
                    nested_failed_dir.mkdir(parents=True, exist_ok=True)

                # Attempt to hardlink the image to the failed directory
                # Copy occurs if hardlink fails ie. cross-device
                if nested_failed_dir.name == image_file.parent.name:
                    failed_img = nested_failed_dir / image_file.name
                else:
                    failed_img = failed_dir / image_file.name
                try:
                    failed_img.hardlink_to(image_file)
                except OSError:
                    # Using copy2 preserves metadata
                    # https://docs.python.org/3/library/shutil.html#shutil.copy2
                    copy2(image_file, failed_img)
                img_dict = {
                    image_file.name: {
                        "missing_tags": redaction_plan.report_plan()[image_file.name].get(
                            "missing_tags", []
                        )
                    }
                }
                failed_images["failed_images"].append(img_dict)
                run_summary.append(
                    {
                        "input_path": image_file,
                        "output_path": "",
                        "detail": "Could not redact with the provided set of rules.",
                    }
                )

            else:
                associated_jpegs = get_associated_outputs(image_file) if export_associated else {}
                redaction_plan.execute_plan()
                output_parent_dir = redact_dir
                if recursive:
                    if image_file.parent in input_paths:
                        parent_index = input_paths.index(image_file.parent)
                    for ancestor in image_file.parents:
                        if ancestor in input_paths:
                            parent_index = input_paths.index(ancestor)
                            break
                    output_parent_dir = Path(
                        str(image_file).replace(str(input_paths[parent_index]), str(redact_dir), 1)
                    ).parent
                    output_parent_dir.mkdir(parents=True, exist_ok=True)
                output_path = (
                    _get_output_path(
                        image_file,
                        output_parent_dir,
                        output_file_name_base,
                        index,
                        output_file_max,
                    )
                    if rename
                    else output_parent_dir / image_file.name
                )
                redaction_plan.save(output_path, overwrite)
                run_summary.append(
                    {
                        "input_path": image_file,
                        "output_path": output_path,
                        "detail": "redacted successfully",
                    }
                )
                for image, jpeg in associated_jpegs.items():  # write associated images to disk
                    associated_parent_dir = Path(
                        str(output_path).replace(str(redact_dir), str(associated_dir / image), 1)
                    ).parent
                    associated_parent_dir.mkdir(parents=True, exist_ok=True)
                    associated_path = associated_parent_dir / f"{output_path.name}.{image}.jpg"
                    associated_path.write_bytes(jpeg.getbuffer())
                if output_file_counter == output_file_max:
                    logger.info("Redactions completed")
                    if failed_img_counter:
                        # Ensure that the logged index is the correct starting point
                        with open(failed_manifest_file, "a") as manifest:
                            yaml.dump(
                                failed_images,
                                manifest,
                                explicit_start=True,
                                default_flow_style=False,
                            )
                            manifest.write("failed_images_count: " + str(failed_img_counter) + "\n")
                            index += 1

                            yaml_command = f"""command: imagedephi run {failed_dir} --output-dir {redact_dir.parent} --index {index}"""  # noqa
                            options = [
                                f" --override-rules {override_rules}" if override_rules else "",
                                " --overwrite" if overwrite else "",
                                f" --profile {profile}" if profile != "default" else "",
                                " --recursive" if recursive else "",
                                " --skip-rename" if not rename else "",
                            ]
                            yaml_command += " ".join(filter(None, options))
                            command = yaml.safe_load(yaml_command)
                            yaml.dump(command, manifest, width=float("inf"))
                index += 1
            output_file_counter += 1
    logger.info(f"Writing manifest to {manifest_file}")
    with open(manifest_file, "w") as manifest:
        fieldnames = ["input_path", "output_path", "detail"]
        writer = DictWriter(manifest, fieldnames=fieldnames)
        writer.writeheader()
        for row in run_summary:
            writer.writerow(row)


def _custom_sort(item):
    key, value = item
    if key == "missing_tags":
        return (0, key)
    elif isinstance(value, dict) and value["action"] == "delete":
        return (1, key)
    else:
        return (2, key)


def _sort_data(data):
    """
    Sort images based on the presence of missing tags and then by image name.

    Sort tags within each image based on the action and tag name.
    """
    sorted_data = {}
    # List of tags that can't be edited and should be excluded from the redaction plan
    excluded_tags = [
        "BigTIFF",
        "FreeByteCounts",
        "FreeOffsets",
        "JPEGIFByteCount",
        "JPEGIFOffset",
        "JPEGTables",
        "NewSubfileType",
        "Photometric",
        "PlanarConfig",
        "Predictor",
        "StripByteCounts",
        "StripOffsets",
        "TileByteCounts",
        "TileOffsets",
    ]

    for image_name, tags in data.items():
        # Remove excluded tags
        for tag in excluded_tags:
            tags.pop(tag, None)
        # Sort tags within each image
        sorted_tags = OrderedDict(sorted(tags.items(), key=_custom_sort))
        tags_used.update(sorted_tags)
        sorted_data[image_name] = sorted_tags
    sorted_data = OrderedDict(
        sorted(sorted_data.items(), key=lambda x: (0 if "missing_tags" in x[1] else 1, x[0]))
    )
    return sorted_data


def show_redaction_plan(
    input_paths: list[Path],
    override_rules: Path | None = None,
    recursive: bool = False,
    require_all: bool = False,
    profile="",
    limit: int | None = None,
    offset: int | None = None,
    update: bool = True,
) -> NamedTuple:
    base_rules = get_base_rules(profile)
    override_ruleset = None
    if override_rules:
        override_ruleset = _get_user_rules(override_rules)
    starting_logging_level = logger.getEffectiveLevel()
    with logging_redirect_tqdm(loggers=[logger]):
        image_paths = generator_to_list_with_progress(
            iter_image_dirs(input_paths, recursive),
            progress_bar_desc="Collecting files to redact...",
        )
    if len(image_paths) == 1:
        # For a single image, log all details of the plan
        logger.setLevel(logging.DEBUG)

    global tags_used
    global missing_rules
    missing_rules = False

    def _create_redaction_plan_report():
        global missing_rules
        global unprocessable_image_messages
        unprocessable_image_messages = []
        with logging_redirect_tqdm(loggers=[logger]):
            for image_path in tqdm(image_paths, desc="Reporting plan", position=0, leave=True):
                try:
                    redaction_plan = build_redaction_plan(image_path, base_rules, override_ruleset)
                except tifftools.TifftoolsError:
                    unprocessable_image_messages.append(f"Could not open {image_path} as a tiff.")
                    continue
                except MalformedAperioFileError:
                    unprocessable_image_messages.append(
                        f"{image_path} could not be processed as a valid Aperio file."
                    )
                    continue
                except UnsupportedFileTypeError as e:
                    unprocessable_image_messages.append(
                        f"{image_path} could not be processed. {e.args[0]}"
                    )
                    continue
                # Handle and report other errors without stopping the process
                except Exception as e:
                    unprocessable_image_messages.append(
                        f"{image_path} could not be processed. {e.args[0]}"
                    )
                    continue
                logger.info(f"Redaction plan for {image_path.name}:")
                redaction_plan_report.update(redaction_plan.report_plan())  # type: ignore
                if not redaction_plan.is_comprehensive():
                    missing_rules = True
                    if require_all:
                        break

    if not update:
        global redaction_plan_report
        redaction_plan_report = {}
        global tags_used
        tags_used = OrderedDict()
        _create_redaction_plan_report()
    else:

        _create_redaction_plan_report()

    total = len(redaction_plan_report)  # type: ignore
    sorted_dict = _sort_data(redaction_plan_report)  # type: ignore
    if limit is not None and offset is not None:
        sorted_dict = OrderedDict(list(sorted_dict.items())[offset * limit : (offset + 1) * limit])
    images_plan = namedtuple("images_plan", ["data", "total", "tags", "missing_rules"])

    for input_path in input_paths:
        if input_path.is_dir():
            # Provide a summary if the input path is a directory of images
            logger.info(f"ImageDePHI summary for {input_path}:")
            incomplete = [
                file_path
                for file_path in redaction_plan_report
                if not redaction_plan_report[file_path]["comprehensive"]
            ]
            logger.info(
                f"{len(image_paths) - (len(incomplete) + len(unprocessable_image_messages))}"
                " images able to be redacted with the provided rule set."
            )
            if incomplete:
                logger.info(
                    f"{len(incomplete)} file(s) could not be redacted with the provided rules."
                )
                logger.info(
                    "The following images could not be redacted given the current rule set:"
                )
                for file in incomplete:
                    logger.info(f"\t{file}")
                logger.info(
                    "For more details about individual images that couldn't be redacted, run "
                    "'imagedephi plan <unredactable_file>'"
                )
            if unprocessable_image_messages:
                logger.info(
                    f"{len(unprocessable_image_messages)} file(s) could not "
                    "be processed by ImageDePHI."
                )

    # Report exceptions outside of the directory level report
    for message in unprocessable_image_messages:
        logger.info(f"\t{message}")

    # Reset logging level if it was changed
    logger.setLevel(starting_logging_level)
    return images_plan(sorted_dict, total, list(tags_used), missing_rules)
