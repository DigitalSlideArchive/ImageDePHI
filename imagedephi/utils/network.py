import asyncio


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
