from __future__ import annotations

from collections import OrderedDict, namedtuple
from collections.abc import Generator
from csv import DictWriter
import datetime
import importlib.resources
from pathlib import Path
from typing import NamedTuple

import tifftools
import tifftools.constants
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
import yaml

from imagedephi.rules import Ruleset
from imagedephi.utils.image import get_file_format_from_path
from imagedephi.utils.logger import logger
from imagedephi.utils.progress_log import push_progress

from .build_redaction_plan import build_redaction_plan
from .svs import MalformedAperioFileError
from .tiff import UnsupportedFileTypeError


def _get_output_path(
    file_path: Path,
    output_dir: Path,
    base_name: str,
    count: int,
    max: int,
) -> Path:
    return output_dir / f"{base_name}_{count:0{len(str(max))}}{file_path.suffix}"


def get_base_rules():
    base_rules_path = importlib.resources.files("imagedephi") / "base_rules.yaml"
    with base_rules_path.open() as base_rules_stream:
        base_rule_set = Ruleset.parse_obj(yaml.safe_load(base_rules_stream))
        return base_rule_set


def iter_image_files(directory: Path, recursive: bool = False) -> Generator[Path, None, None]:
    """Given a directory return an iterable of available images."""
    for child in sorted(directory.iterdir()):
        # Use first four bits to check if its a tiff file
        if child.is_file():
            file_format = None
            try:
                file_format = get_file_format_from_path(child)
            except PermissionError:
                # Don't attempt to redact inaccessible files
                pass
            if file_format:
                yield child
        elif child.is_dir() and recursive:
            yield from iter_image_files(child, recursive)


def create_redact_dir_and_manifest(base_output_dir: Path) -> tuple[Path, Path]:
    """
    Given a directory, create and return a sub-directory within it.

    `identifier` should be a unique string for the new directory. If no value
    is supplied, a timestamp is used.
    """
    time_stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    redact_dir = base_output_dir / f"Redacted_{time_stamp}"
    manifest_file = base_output_dir / f"Redacted_{time_stamp}_manifest.csv"
    try:
        redact_dir.mkdir(parents=True)
        manifest_file.touch()
    except PermissionError:
        logger.error("Cannnot create an output directory, permission error.")
        raise
    else:
        logger.info(f"Created redaction folder: {redact_dir}")
        return redact_dir, manifest_file


def redact_images(
    input_path: Path,
    output_dir: Path,
    override_rules: Ruleset | None = None,
    rename: bool = True,
    overwrite: bool = False,
    recursive: bool = False,
) -> None:
    # Keep track of information about this run to write to a persistent log file (csv?)
    # (original_name, output_name) as bare minimum
    # error message? rule set (base/override)?
    run_summary = []
    base_rules = get_base_rules()
    output_file_name_base = (
        override_rules.output_file_name if override_rules else base_rules.output_file_name
    )
    # Convert to a list in order to get the length
    images_to_redact = list(
        iter_image_files(input_path, recursive) if input_path.is_dir() else [input_path]
    )
    output_file_counter = 1
    output_file_max = len(images_to_redact)
    redact_dir, manifest_file = create_redact_dir_and_manifest(output_dir)

    dcm_uid_map: dict[str, str] = {}

    with logging_redirect_tqdm(loggers=[logger]):
        for image_file in tqdm(images_to_redact, desc="Redacting images", position=0, leave=True):
            push_progress(output_file_counter, output_file_max)
            try:
                redaction_plan = build_redaction_plan(
                    image_file, base_rules, override_rules, dcm_uid_map=dcm_uid_map
                )
            # Handle and report other errors without stopping the process
            except Exception as e:
                logger.error(f"{image_file.name} could not be processed. {e.args[0]}")
                continue
            if not redaction_plan.is_comprehensive():
                logger.info(f"Redaction could not be performed for {image_file.name}.")
                redaction_plan.report_missing_rules()
            else:
                redaction_plan.report_plan()
                redaction_plan.execute_plan()
                output_parent_dir = redact_dir
                if recursive:
                    output_parent_dir = Path(
                        str(image_file).replace(str(input_path), str(redact_dir), 1)
                    ).parent
                    output_parent_dir.mkdir(parents=True, exist_ok=True)
                output_path = (
                    _get_output_path(
                        image_file,
                        output_parent_dir,
                        output_file_name_base,
                        output_file_counter,
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
                    }
                )
                if output_file_counter == output_file_max:
                    logger.info("Redactions completed")
            output_file_counter += 1
    logger.info(f"Writing manifest to {manifest_file}")
    with open(manifest_file, "w") as manifest:
        fieldnames = ["input_path", "output_path"]
        writer = DictWriter(manifest, fieldnames=fieldnames)
        writer.writeheader()
        for row in run_summary:
            writer.writerow(row)


def show_redaction_plan(
    input_path: Path,
    override_rules: Ruleset | None = None,
    recursive=False,
    limit: int | None = None,
    offset: int | None = None,
    update: bool = True,
) -> NamedTuple:
    image_paths = iter_image_files(input_path, recursive) if input_path.is_dir() else [input_path]
    base_rules = get_base_rules()

    if update:
        global redaction_plan_report
        redaction_plan_report = {}  # type: ignore
        for image_path in image_paths:
            try:
                redaction_plan = build_redaction_plan(image_path, base_rules, override_rules)
            except tifftools.TifftoolsError:
                logger.error(f"Could not open {image_path.name} as a tiff.")
                continue
            except MalformedAperioFileError:
                logger.error(f"{image_path.name} could not be processed as a valid Aperio file.")
                continue
            except UnsupportedFileTypeError as e:
                logger.error(f"{image_path.name} could not be processed. {e.args[0]}")
                continue
            # Handle and report other errors without stopping the process
            except Exception as e:
                logger.error(f"{image_path.name} could not be processed. {e.args[0]}")
                continue
            logger.info(f"Redaction plan for {image_path.name}")
            redaction_plan_report.update(redaction_plan.report_plan())  # type: ignore
    total = len(redaction_plan_report)  # type: ignore
    sorted_dict = OrderedDict(
        sorted(
            redaction_plan_report.items(),  # type: ignore
            key=lambda item: "missing_tags" not in item[1],
        )
    )
    if limit is not None and offset is not None:
        sorted_dict = OrderedDict(list(sorted_dict.items())[offset : limit + offset])
    images_plan = namedtuple("images_plan", ["data", "total"])

    return images_plan(sorted_dict, total)
