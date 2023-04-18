import sys

import pytest
from pytest_mock import MockerFixture

from imagedephi.utils.os import launched_from_frozen_binary, launched_from_windows_explorer


@pytest.mark.parametrize("frozen", [False, True])
def test_utils_os_launched_from_frozen_binary(frozen: bool, mocker: MockerFixture) -> None:
    mocker.patch("sys.frozen", new=frozen, create=True)

    result = launched_from_frozen_binary()

    assert result is frozen


@pytest.mark.skipif(sys.platform == "win32", reason="non-windows only")
def test_utils_os_launched_from_windows_explorer_nonwindows() -> None:
    result = launched_from_windows_explorer()

    assert result is False


@pytest.mark.skipif(sys.platform != "win32", reason="windows only")
@pytest.mark.parametrize(
    "frozen,process_count,expected",
    [
        (False, 1, True),
        (False, 3, False),
        (True, 2, True),
        (True, 3, False),
    ],
    ids=["non-frozen explorer", "non-frozen console", "frozen explorer", "frozen console"],
)
def test_utils_os_launched_from_windows_explorer_windows(
    frozen: bool, process_count: int, expected: bool, mocker: MockerFixture
) -> None:
    mocker.patch("imagedephi.utils.os.launched_from_frozen_binary", return_value=frozen)
    mocker.patch("ctypes.windll.kernel32.GetConsoleProcessList", return_value=process_count)

    result = launched_from_windows_explorer()

    assert result is expected
