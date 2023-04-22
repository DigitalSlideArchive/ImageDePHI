from inspect import iscoroutinefunction

import click
from click.testing import CliRunner
import pytest
from pytest_mock import MockerFixture

from imagedephi.utils.cli import FallthroughGroup, run_coroutine


def test_utils_cli_run_coroutine(mocker: MockerFixture) -> None:
    async_mock = mocker.AsyncMock()

    wrapped = run_coroutine(async_mock)

    assert not iscoroutinefunction(wrapped)
    wrapped(5, foo="bar")
    async_mock.assert_awaited_once_with(5, foo="bar")


def test_utils_cli_fallthrough_group_baseline(mocker: MockerFixture, cli_runner: CliRunner) -> None:
    cmd = mocker.Mock()
    sub = mocker.Mock()
    should_fallthrough = mocker.Mock()
    # Decorators can't be used with mocks, so create the group and subcommands here
    cmd_group = FallthroughGroup(
        subcommand_name="sub", should_fallthrough=should_fallthrough, callback=cmd
    )
    cmd_group.add_command(click.Command(name="sub", callback=sub))

    # Explicitly invoke a subcommand
    result = cli_runner.invoke(cmd_group, ["sub"])

    assert result.exit_code == 0
    cmd.assert_called_once()
    sub.assert_called_once()
    should_fallthrough.assert_not_called()
    assert "Usage" not in result.output


@pytest.mark.parametrize("should_fallthrough", [False, True])
def test_utils_cli_fallthrough_group_empty(
    should_fallthrough: bool, mocker: MockerFixture, cli_runner: CliRunner
) -> None:
    cmd = mocker.Mock()
    sub = mocker.Mock()
    cmd_group = FallthroughGroup(
        subcommand_name="sub", should_fallthrough=lambda: should_fallthrough, callback=cmd
    )
    cmd_group.add_command(click.Command(name="sub", callback=sub))

    # No subcommand
    result = cli_runner.invoke(cmd_group, [])

    assert result.exit_code == 0
    assert cmd.called is should_fallthrough
    assert sub.called is should_fallthrough
    assert ("Usage" in result.output) is not should_fallthrough
