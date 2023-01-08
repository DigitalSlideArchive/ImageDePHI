import asyncio
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import ParamSpec, TypeVar

T = TypeVar("T")
P = ParamSpec("P")


def run_coroutine(f: Callable[P, Coroutine[None, None, T]]) -> Callable[P, T]:
    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return asyncio.run(f(*args, **kwargs))

    return wrapper


async def wait_for_port(port: int, host: str = "127.0.0.1") -> None:
    """Block until a TCP port on the specified host can be opened."""
    while True:
        try:
            _, writer = await asyncio.open_connection(host, port)
        except ConnectionRefusedError:
            pass
        else:
            writer.close()
            await writer.wait_closed()
            return
