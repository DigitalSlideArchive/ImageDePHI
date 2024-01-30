import abc
from pathlib import Path

from imagedephi.rules import FileFormat


class RedactionPlan:
    file_format: FileFormat

    @abc.abstractmethod
    def report_plan(self) -> None: ...

    @abc.abstractmethod
    def execute_plan(self) -> None: ...

    @abc.abstractmethod
    def is_comprehensive(self) -> bool:
        """Return whether the plan redacts all metadata and/or images needed."""
        ...

    @abc.abstractmethod
    def report_missing_rules(self) -> None: ...

    @abc.abstractmethod
    def save(self, output_path: Path, overwrite: bool) -> None: ...
