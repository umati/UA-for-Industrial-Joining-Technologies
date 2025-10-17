#!/usr/bin/env python3
import asyncio
import websockets
import json
import traceback
import os
import signal
import platform
from typing import Optional
from dotenv import load_dotenv
from Python.IJTInterface import IJTInterface
from Python.IJTLogger import ijt_log


# Load environment variables
load_dotenv()

opcuaHandler: Optional[IJTInterface] = None
websocket_server = None


# WebSocket handler
async def handler(websocket):
    global opcuaHandler
    client_ip = websocket.remote_address[0]
    ijt_log.info(f"Client connected: {client_ip}")
    if opcuaHandler is None:
        opcuaHandler = IJTInterface()
    try:
        async for message in websocket:
            mess = json.loads(message)
            await opcuaHandler.handle(websocket, mess)
    except websockets.exceptions.ConnectionClosed:
        ijt_log.info(f"Client disconnected: {client_ip}")
    except Exception:
        ijt_log.error("Exception in handler:")
        ijt_log.error(traceback.format_exc())


# Graceful shutdown
async def shutdown():
    ijt_log.info("Shutting down gracefully...")
    if opcuaHandler:
        await opcuaHandler.disconnect()
    if websocket_server:
        websocket_server.close()
        await websocket_server.wait_closed()

    ijt_log.info("Shutdown complete.")


# Main entry
async def main():
    global websocket_server
    try:
        port = int(os.getenv("WS_PORT", 8001))
    except ValueError:
        ijt_log.error("Invalid WS_PORT environment variable. Falling back to 8001.")
        port = 8001

    websocket_server = await websockets.serve(handler, "localhost", port)
    ijt_log.info(f"WebSocket server running on ws://localhost:{port}")
    ijt_log.info("Server setup complete. Awaiting connections...")

    loop = asyncio.get_running_loop()

    # Signal handling for graceful shutdown
    if platform.system() != "Windows":
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
            except NotImplementedError:
                ijt_log.warning(
                    f"Signal handling not supported for {sig} on this platform."
                )
    else:
        # Windows fallback: listen for shutdown via a background task
        async def windows_shutdown_monitor():
            while True:
                await asyncio.sleep(1)

        asyncio.create_task(windows_shutdown_monitor())

    try:
        await asyncio.Future()  # Run forever
    finally:
        ijt_log.warning("main() exiting — attempting shutdown cleanup.")
        await shutdown()


# Entry point
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
