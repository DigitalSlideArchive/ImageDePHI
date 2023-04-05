import asyncio
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import ParamSpec, TypeVar

T = TypeVar("T")
P = ParamSpec("P")


def run_coroutine(f: Callable[P, Coroutine[None, None, T]]) -> Callable[P, T]:
    """Decorate an async function to be run in a new event loop."""

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return asyncio.run(f(*args, **kwargs))

    return wrapper
