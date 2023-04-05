from inspect import iscoroutinefunction

from pytest_mock import MockerFixture

from imagedephi.utils.cli import run_coroutine


def test_utils_cli_run_coroutine(mocker: MockerFixture) -> None:
    async_mock = mocker.AsyncMock()

    wrapped = run_coroutine(async_mock)

    assert not iscoroutinefunction(wrapped)
    wrapped(5, foo="bar")
    async_mock.assert_awaited_once_with(5, foo="bar")
