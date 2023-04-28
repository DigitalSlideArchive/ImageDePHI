import abc

from imagedephi.models.rules import FileFormat

FILE_EXTENSION_MAP: dict[str, FileFormat] = {
    ".tif": FileFormat.TIFF,
    ".tiff": FileFormat.TIFF,
    ".svs": FileFormat.SVS,
}


class RedactionPlan:
    file_format: FileFormat

    @abc.abstractmethod
    def report_plan(self) -> None:
        ...

    @abc.abstractmethod
    def execute_plan(self) -> None:
        ...

    @abc.abstractmethod
    def is_comprehensive(self) -> bool:
        """Return whether the plan redacts all metadata and/or images needed."""
        ...

    @abc.abstractmethod
    def report_missing_rules(self) -> None:
        ...
