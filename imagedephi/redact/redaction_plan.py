from __future__ import annotations

import abc
from pathlib import Path
from typing import TYPE_CHECKING

from imagedephi.rules import FileFormat

if TYPE_CHECKING:
    from tifftools.tifftools import TagData

    ByteInfo = dict[str, str | int]

    TagRedactionPlan = dict[str, int | float | TagData | ByteInfo]

    RedactionPlanReport = dict[str, dict[str, int | str | TagRedactionPlan]]


class RedactionPlan:
    file_format: FileFormat

    @abc.abstractmethod
    def report_plan(self) -> RedactionPlanReport: ...

    @abc.abstractmethod
    def execute_plan(self) -> None: ...

    @abc.abstractmethod
    def is_comprehensive(self) -> bool:
        """Return whether the plan redacts all metadata and/or images needed."""
        ...

    @abc.abstractmethod
    def report_missing_rules(self, report=None) -> None: ...

    @abc.abstractmethod
    def save(self, output_path: Path, overwrite: bool) -> None: ...
