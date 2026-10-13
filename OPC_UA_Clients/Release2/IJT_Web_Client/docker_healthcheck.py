#!/usr/bin/env python3
"""Container health: HTTP UI reachable and WebSocket upgrade handshake succeeds."""

from __future__ import annotations

import asyncio
import http.client
import os


def _check_http(port: str) -> None:
    connection = http.client.HTTPConnection("127.0.0.1", int(port), timeout=5)
    try:
        connection.request("GET", "/")
        response = connection.getresponse()
        response.read(1)
        if response.status >= 500:
            raise RuntimeError(f"HTTP healthcheck status {response.status}")
    finally:
        connection.close()


async def _check_websocket(port: str) -> None:
    import websockets

    async with websockets.connect(
        f"ws://127.0.0.1:{port}",
        open_timeout=5,
        close_timeout=1,
    ):
        return


def main() -> int:
    http_port = os.environ.get("HTTP_PORT", "3000")
    ws_port = os.environ.get("WS_PORT", "8001")
    try:
        _check_http(http_port)
        asyncio.run(_check_websocket(ws_port))
    except Exception:  # noqa: BLE001 - healthcheck must fail closed on any probe error
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
