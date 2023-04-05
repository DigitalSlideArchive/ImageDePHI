import asyncio
import socket


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


def unused_tcp_port() -> int:
    with socket.socket() as sock:
        # Ensure the port can be immediately reused
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Specifying 0 as the port will select a dynamic ephimeral port
        sock.bind(("127.0.0.1", 0))
        _, sock_port = sock.getsockname()
        return sock_port
