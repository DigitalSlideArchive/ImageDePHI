import asyncio
from collections.abc import AsyncGenerator
from inspect import iscoroutinefunction

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from imagedephi.async_utils import run_coroutine, wait_for_port


@pytest_asyncio.fixture
async def server(unused_tcp_port: int) -> AsyncGenerator[asyncio.Server, None]:
    def server_callback(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        pass

    server = await asyncio.start_server(server_callback, "127.0.0.1", unused_tcp_port)
    async with server:
        yield server


def test_async_utils_run_coroutine(mocker: MockerFixture) -> None:
    async_mock = mocker.AsyncMock()

    wrapped = run_coroutine(async_mock)

    assert not iscoroutinefunction(wrapped)
    wrapped(5, foo="bar")
    async_mock.assert_awaited_once_with(5, foo="bar")


@pytest.mark.timeout(1)
@pytest.mark.asyncio
async def test_async_utils_wait_for_port(server: asyncio.Server, unused_tcp_port: int) -> None:
    await wait_for_port(unused_tcp_port)
