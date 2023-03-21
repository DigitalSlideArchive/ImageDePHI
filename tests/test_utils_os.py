import sys

import pytest
from pytest_mock import MockerFixture

from imagedephi.utils.os import launched_from_windows_explorer


@pytest.mark.skipif(sys.platform == "win32", reason="non-windows only")
def test_utils_os_launched_from_windows_explorer_nonwindows() -> None:
    result = launched_from_windows_explorer()

    assert result is False


@pytest.mark.skipif(sys.platform != "win32", reason="windows only")
@pytest.mark.parametrize(
    "process_count,expected_return", [(1, True), (3, False)], ids=["true", "false"]
)
def test_utils_os_launched_from_windows_explorer_windows(
    process_count: int, expected_return: bool, mocker: MockerFixture
) -> None:
    mocker.patch("imagedephi.utils.os.launched_from_frozen_binary", return_value=False)
    mocker.patch("ctypes.windll.kernel32.GetConsoleProcessList", return_value=process_count)

    result = launched_from_windows_explorer()

    assert result is expected_return
