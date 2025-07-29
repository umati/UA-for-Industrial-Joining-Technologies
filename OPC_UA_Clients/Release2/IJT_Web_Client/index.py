#!/usr/bin/env python3
import asyncio
import websockets
import json
import logging
import traceback
import os
import signal
import platform
from typing import Optional
from dotenv import load_dotenv
from Python.IJTInterface import IJTInterface

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

opcuaHandler: Optional[IJTInterface] = None
websocket_server = None

# ✅ For websockets >= 11.0: handler takes only one argument
async def handler(websocket):
    global opcuaHandler
    client_ip = websocket.remote_address[0]
    log.info(f"Client connected: {client_ip}")

    if opcuaHandler is None:
        opcuaHandler = IJTInterface()

    try:
        async for message in websocket:
            mess = json.loads(message)
            await opcuaHandler.handle(websocket, mess)
    except websockets.exceptions.ConnectionClosed:
        log.info(f"Client disconnected: {client_ip}")
    except Exception:
        log.error("Exception in handler:")
        log.error(traceback.format_exc())

async def shutdown():
    log.info("Shutting down gracefully...")
    if websocket_server:
        websocket_server.close()
        await websocket_server.wait_closed()
    if opcuaHandler:
        await opcuaHandler.disconnect()
    log.info("Shutdown complete.")

async def main():
    global websocket_server
    try:
        port = int(os.getenv("WS_PORT", 8001))
    except ValueError:
        log.error("Invalid WS_PORT environment variable. Falling back to 8001.")
        port = 8001

    # ✅ websockets.serve(handler, host, port) — no path argument needed
    websocket_server = await websockets.serve(handler, "localhost", port)
    log.info(f"WebSocket server running on ws://localhost:{port}")

    loop = asyncio.get_running_loop()

    if platform.system() != "Windows":
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
            except NotImplementedError:
                log.warning(f"Signal handling not supported for {sig} on this platform.")

    await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Server stopped by user.")
        asyncio.run(shutdown())
    except Exception:
        log.error("Unhandled exception:")
        log.error(traceback.format_exc())
