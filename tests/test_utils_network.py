import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

from imagedephi.utils.network import wait_for_port


@pytest_asyncio.fixture
async def server(unused_tcp_port: int) -> AsyncGenerator[asyncio.Server, None]:
    def server_callback(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        pass

    server = await asyncio.start_server(server_callback, "127.0.0.1", unused_tcp_port)
    async with server:
        yield server
        server.sockets[0]


@pytest.mark.timeout(1)
@pytest.mark.asyncio
async def test_utils_network_wait_for_port(server: asyncio.Server) -> None:
    server_port = server.sockets[0].getsockname()[1]

    await wait_for_port(server_port)
