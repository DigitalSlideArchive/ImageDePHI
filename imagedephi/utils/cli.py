import asyncio
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import click

T = TypeVar("T")
P = ParamSpec("P")


def run_coroutine(f: Callable[P, Coroutine[None, None, T]]) -> Callable[P, T]:
    """Decorate an async function to be run in a new event loop."""

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return asyncio.run(f(*args, **kwargs))

    return wrapper


class FallthroughGroup(click.Group):
    """A Group which may run a subcommand when no subcommand is specified."""

    def __init__(self, subcommand_name: str, should_fallthrough: Callable[[], bool], **attrs: Any):
        # Subcommands are not added until after this is instantiated,
        # so only store the future subcommand name
        self.subcommand_name = subcommand_name
        self.should_fallthrough = should_fallthrough

        attrs["invoke_without_command"] = True
        attrs["no_args_is_help"] = False
        super().__init__(**attrs)

    def invoke(self, ctx: click.Context) -> Any:
        # If no subcommand is specified.
        # Use this test, since "ctx.invoked_subcommand" is not set yet.
        if not ctx.protected_args:
            if self.should_fallthrough():
                # Subcommands are stored in "ctx.protected_args", so fake a call by prepending it
                # Calling "ctx.invoke" directly here would not allow the parent command to run
                ctx.protected_args.insert(0, self.subcommand_name)
            elif not ctx.resilient_parsing:
                # Execute the normal Click "no_args_is_help" behavior
                click.echo(ctx.get_help(), color=ctx.color)
                ctx.exit()
        elif ctx.protected_args and ctx.protected_args[0] not in self.commands:
            # If the subcommand stored in "ctx.protected_args" is not a real
            # subcommand, show the entire help text in addition to the "no such
            # command" mesasge.
            click.echo(f"Error: No such command: '{ctx.protected_args[0]}'.")
            click.echo(ctx.get_help(), color=ctx.color)
            ctx.exit()

        # All non-help cases reach here
        return super().invoke(ctx)
