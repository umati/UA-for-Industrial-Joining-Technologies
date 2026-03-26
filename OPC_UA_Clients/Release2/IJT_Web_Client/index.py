#!/usr/bin/env python3
import asyncio
import contextlib
import json
import os
import platform
import signal
import sys
import time
import traceback
from pathlib import Path
from typing import Set

_SRC = str(Path(__file__).resolve().parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import websockets
from dotenv import load_dotenv

from python.ijt_interface import IJTInterface
from python.ijt_logger import ijt_log

# Load environment variables
load_dotenv()

websocket_server = None
active_handlers: Set[IJTInterface] = set()
active_websockets: Set[websockets.ServerConnection] = set()
active_handlers_lock = asyncio.Lock()
shutdown_lock = asyncio.Lock()
shutdown_started = False


async def handler(websocket):
    """Handle one browser websocket session and isolate OPC UA state per client."""
    global shutdown_started
    if shutdown_started:
        await websocket.close(code=1012, reason="Server shutting down")
        return

    client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
    ijt_log.info(f"Client connected: {client_ip}")

    opcua_handler = IJTInterface()
    async with active_handlers_lock:
        active_handlers.add(opcua_handler)
        active_websockets.add(websocket)

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
            active_websockets.discard(websocket)


async def shutdown():
    """Graceful shutdown for all active websocket sessions and OPC UA connections."""
    global websocket_server, shutdown_started
    async with shutdown_lock:
        if shutdown_started:
            return
        shutdown_started = True

        ijt_log.info("Shutting down gracefully...")

        # Stop accepting new websocket connections first.
        if websocket_server:
            websocket_server.close()
            await websocket_server.wait_closed()
            websocket_server = None

        async with active_handlers_lock:
            handlers = list(active_handlers)
            sockets = list(active_websockets)
            active_handlers.clear()
            active_websockets.clear()

        # Ask active websocket clients to close, so per-client cleanup paths execute promptly.
        for ws in sockets:
            with contextlib.suppress(Exception):
                await ws.close(code=1001, reason="Server shutdown")

        if handlers:
            await asyncio.gather(
                *(handler.disconnect() for handler in handlers),
                return_exceptions=True,
            )

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
        def _schedule_shutdown_from_signal(signum, _frame):
            ijt_log.info(f"Windows signal received ({signum}). Scheduling graceful shutdown.")
            loop.call_soon_threadsafe(lambda: asyncio.create_task(shutdown()))

        windows_signals = [signal.SIGINT]
        if hasattr(signal, "SIGBREAK"):
            windows_signals.append(signal.SIGBREAK)
        if hasattr(signal, "SIGTERM"):
            windows_signals.append(signal.SIGTERM)
        for sig in windows_signals:
            with contextlib.suppress(Exception):
                signal.signal(sig, _schedule_shutdown_from_signal)

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
