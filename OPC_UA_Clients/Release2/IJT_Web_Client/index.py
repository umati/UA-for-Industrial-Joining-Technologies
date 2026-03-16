#!/usr/bin/env python3
import asyncio
import json
import os
import platform
import signal
import time
import traceback
from typing import Set

import websockets
from dotenv import load_dotenv

from Python.ijt_interface import IJTInterface
from Python.ijt_logger import ijt_log

# Load environment variables
load_dotenv()

websocket_server = None
active_handlers: Set[IJTInterface] = set()
active_handlers_lock = asyncio.Lock()


async def handler(websocket):
    """Handle one browser websocket session and isolate OPC UA state per client."""
    client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
    ijt_log.info(f"Client connected: {client_ip}")

    opcua_handler = IJTInterface()
    async with active_handlers_lock:
        active_handlers.add(opcua_handler)

    try:
        async for message in websocket:
            try:
                payload = json.loads(message)
            except json.JSONDecodeError as exc:
                await websocket.send(
                    json.dumps(
                        {
                            "command": "invalid request",
                            "endpoint": "common",
                            "data": {"exception": f"Invalid JSON payload: {exc.msg}"},
                            "error": {
                                "code": "INVALID_JSON",
                                "message": "Request payload is not valid JSON.",
                            },
                        }
                    )
                )
                continue

            await opcua_handler.handle(websocket, payload)
    except websockets.exceptions.ConnectionClosed:
        ijt_log.info(f"Client disconnected: {client_ip}")
    except Exception:
        ijt_log.error("Exception in websocket handler:")
        ijt_log.error(traceback.format_exc())
    finally:
        ijt_log.info(f"Cleaning up for client: {client_ip}")
        await opcua_handler.disconnect()
        async with active_handlers_lock:
            active_handlers.discard(opcua_handler)


async def shutdown():
    """Graceful shutdown for all active websocket sessions and OPC UA connections."""
    global websocket_server
    ijt_log.info("Shutting down gracefully...")

    async with active_handlers_lock:
        handlers = list(active_handlers)
        active_handlers.clear()

    if handlers:
        await asyncio.gather(
            *(handler.disconnect() for handler in handlers),
            return_exceptions=True,
        )

    if websocket_server:
        websocket_server.close()
        await websocket_server.wait_closed()
        websocket_server = None

    ijt_log.info("Shutdown complete.")


async def main():
    """Main entrypoint for websocket server."""
    global websocket_server

    try:
        port = int(os.getenv("WS_PORT", 8001))
    except ValueError:
        ijt_log.error("Invalid WS_PORT environment variable. Falling back to 8001.")
        port = 8001

    host = "0.0.0.0"
    start_time = time.time()
    websocket_server = await websockets.serve(handler, host, port)
    elapsed = time.time() - start_time

    ijt_log.info(
        "\n========================================"
        "\n WebSocket server started successfully."
        f"\n Local Access:   ws://localhost:{port}"
        "\n Remote Access:  Use your server IP"
        f"\n Bound in {elapsed:.2f} seconds"
        "\n========================================"
    )
    ijt_log.info("Server setup complete. Awaiting connections...")

    loop = asyncio.get_running_loop()

    if platform.system() != "Windows":
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
            except NotImplementedError:
                ijt_log.warning(
                    f"Signal handling not supported for {sig} on this platform."
                )
    else:

        async def windows_shutdown_monitor():
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                ijt_log.info("Windows shutdown monitor cancelled.")
                await shutdown()

        asyncio.create_task(windows_shutdown_monitor())

    try:
        await asyncio.Future()  # Run forever
    finally:
        ijt_log.warning("main() exiting - attempting shutdown cleanup.")
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        ijt_log.info("Server stopped by user (KeyboardInterrupt).")
        asyncio.run(shutdown())
    except Exception:
        ijt_log.error("Unhandled exception:")
        ijt_log.error(traceback.format_exc())
        asyncio.run(shutdown())
